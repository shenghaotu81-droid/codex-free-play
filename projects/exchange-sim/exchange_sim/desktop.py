"""Native Tk desktop. Simulation and rendering also run without a display."""
import json
import time
import tkinter as tk
from tkinter import ttk, filedialog
from PIL import ImageTk
from .world import load_config
from .runtime import PROJECT,make_world,save_run
from .render import dashboard


class Desktop:
    def __init__(self,root,config,args):
        self.root=root; self.args=args; self.running=False; self.last_draw=0.; self.world=None
        root.title('Exchange Lab · 一分钟视觉自动兑换仿真')
        root.geometry('1480x980'); root.minsize(1080,740); root.configure(bg='#0b111c')
        style=ttk.Style(root); style.theme_use('clam')
        style.configure('TFrame',background='#131e2c')
        style.configure('TLabel',background='#131e2c',foreground='#e5edf5')
        style.configure('TButton',padding=(10,7))
        bar=ttk.Frame(root,padding=10); bar.pack(fill='x')
        self.start=ttk.Button(bar,text='开始 60s',command=self.toggle); self.start.pack(side='left',padx=3)
        ttk.Button(bar,text='单步',command=self.single).pack(side='left',padx=3)
        ttk.Button(bar,text='应用参数 / 重置',command=self.reset).pack(side='left',padx=3)
        ttk.Button(bar,text='保存本次结果',command=self.save).pack(side='left',padx=3)
        ttk.Label(bar,text='播放速度').pack(side='left',padx=(18,4))
        self.speed=tk.StringVar(value='1x')
        speeds=ttk.Combobox(bar,textvariable=self.speed,values=['1x','2x','4x','8x'],width=5,state='readonly')
        speeds.pack(side='left'); speeds.bind('<<ComboboxSelected>>',lambda _:self.anchor())
        self.vision=tk.StringVar(value=args.vision)
        ttk.Label(bar,text='感知').pack(side='left',padx=(18,4))
        ttk.Combobox(bar,textvariable=self.vision,values=list(dict.fromkeys([args.vision,'auto','campus','baseline','none'])),width=10,state='readonly').pack(side='left')

        body=ttk.Panedwindow(root,orient='horizontal'); body.pack(fill='both',expand=True,padx=10,pady=(0,10))
        view=ttk.Frame(body); body.add(view,weight=4)
        self.canvas=tk.Canvas(view,bg='#0b111c',highlightthickness=0); self.canvas.pack(fill='both',expand=True)
        side=ttk.Frame(body,padding=10); body.add(side,weight=1)
        ttk.Label(side,text='场景参数（SI 单位）',font=('',13,'bold')).pack(anchor='w')
        row=ttk.Frame(side); row.pack(fill='x',pady=8)
        self.mode=tk.StringVar(value=config['target']['mode'])
        ttk.Combobox(row,textvariable=self.mode,values=['fixed','intermittent','uniform','random'],state='readonly',width=14).pack(side='left')
        ttk.Button(row,text='设置运动模式',command=self.set_mode).pack(side='left',padx=5)
        ttk.Label(side,text='修改 JSON 后点“应用参数 / 重置”。\n相同 seed 可重复对照；参数均为可调模型。').pack(anchor='w',pady=(0,8))
        self.editor=tk.Text(side,width=39,wrap='none',bg='#0e1722',fg='#c8e4ef',insertbackground='white',font=('monospace',10),undo=True)
        scroll=ttk.Scrollbar(side,command=self.editor.yview); self.editor.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right',fill='y'); self.editor.pack(fill='both',expand=True)
        self.editor.insert('1.0',json.dumps(config,indent=2))
        buttons=ttk.Frame(side); buttons.pack(fill='x',pady=(8,0))
        ttk.Button(buttons,text='载入 JSON',command=self.load).pack(side='left')
        ttk.Button(buttons,text='保存参数',command=self.save_config).pack(side='left',padx=5)
        self.status=tk.StringVar(value='就绪。左侧为模拟相机与独立评分视图；右侧参数可编辑。')
        ttk.Label(root,textvariable=self.status,padding=10,wraplength=1400).pack(fill='x')
        root.protocol('WM_DELETE_WINDOW',self.close)
        self.reset()
        root.after(15,self.tick)

    def anchor(self):
        self.anchor_wall=time.monotonic(); self.anchor_sim=self.world.time if self.world else 0.

    def reset(self):
        self.running=False; self.start.configure(text='开始 / 继续')
        try:
            config=load_config(json.loads(self.editor.get('1.0','end')))
            replacement=make_world(config,self.vision.get(),self.args.policy,self.args.campus_config)
            replacement.image=replacement.render_camera()
            if self.world: self.world.close()
            self.world=replacement; self.mode.set(config['target']['mode']); self.anchor()
            self.status.set(f"已重置：{self.world.provenance['vision']} · seed {config['seed']}。点击开始。")
            self.draw()
            return True
        except Exception as exc:
            self.status.set(f'参数未应用：{exc}')

    def toggle(self):
        if not self.world: self.reset()
        if not self.world: return
        if self.running:
            self.running=False; self.start.configure(text='继续'); return
        try:
            dirty=load_config(json.loads(self.editor.get('1.0','end')))!=self.world.c
        except Exception as exc:
            self.status.set(str(exc)); return
        if dirty or self.world.time>=self.world.c['duration_s'] or self.vision.get()!=self.world.provenance.get('requested_vision'):
            if not self.reset(): return
        if self.world:
            self.running=True; self.anchor(); self.start.configure(text='暂停')

    def single(self):
        self.running=False; self.start.configure(text='继续')
        try:
            if self.world: self.world.step(); self.draw()
        except Exception as exc: self.status.set(f'算法运行错误：{exc}')

    def tick(self):
        try:
            if self.running and self.world:
                goal=self.anchor_sim+(time.monotonic()-self.anchor_wall)*float(self.speed.get()[:-1])
                for _ in range(6):
                    if self.world.time>=goal: break
                    if not self.world.step():
                        self.running=False; self.start.configure(text='重新开始'); self.save(); break
            if time.monotonic()-self.last_draw>.1: self.draw()
        except Exception as exc:
            self.running=False; self.start.configure(text='继续'); self.status.set(f'算法运行错误：{exc}')
        self.root.after(15,self.tick)

    def draw(self):
        if not self.world: return
        width=max(640,self.canvas.winfo_width()); height=max(420,self.canvas.winfo_height())
        scale=min(width/1360,height/900); size=(int(1360*scale),int(900*scale))
        self.photo=ImageTk.PhotoImage(dashboard(self.world,self.world.provenance['vision'],size))
        self.canvas.delete('all'); self.canvas.create_image(width/2,height/2,image=self.photo)
        self.last_draw=time.monotonic()

    def set_mode(self):
        try:
            config=json.loads(self.editor.get('1.0','end')); config['target']['mode']=self.mode.get()
            self.editor.delete('1.0','end'); self.editor.insert('1.0',json.dumps(config,indent=2)); self.reset()
        except Exception as exc: self.status.set(str(exc))

    def load(self):
        path=filedialog.askopenfilename(initialdir=PROJECT/'configs',filetypes=[('JSON','*.json')])
        if path:
            try:
                config=load_config(path); self.editor.delete('1.0','end'); self.editor.insert('1.0',json.dumps(config,indent=2)); self.reset()
            except Exception as exc: self.status.set(str(exc))

    def save_config(self):
        try:
            config=load_config(json.loads(self.editor.get('1.0','end')))
            path=PROJECT/'.local/configs/desktop.json'; path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(json.dumps(config,indent=2)+'\n'); self.status.set(f'参数已保存：{path}')
        except Exception as exc: self.status.set(str(exc))

    def save(self):
        if self.world:
            try:
                path=save_run(self.world)
                self.status.set(f'结果已保存：{path} · 入框 {self.world.hits} / 误投 {self.world.misses}')
            except Exception as exc: self.status.set(str(exc))

    def close(self):
        self.running=False
        if self.world: self.world.close()
        self.root.destroy()


def launch(config,args):
    try: root=tk.Tk()
    except tk.TclError as exc:
        raise RuntimeError('无桌面显示连接；请使用 --headless（可加 --video 导出演示）') from exc
    Desktop(root,config,args)
    root.mainloop()
