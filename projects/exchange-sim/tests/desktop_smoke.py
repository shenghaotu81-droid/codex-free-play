"""Exercise native Tk widgets and pause/reset/export. CPU only, no browser/WebGL."""
import argparse
import json
from pathlib import Path
import sys
import tkinter as tk

PROJECT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PROJECT))
from exchange_sim.desktop import Desktop
from exchange_sim.world import load_config


def main():
    root=tk.Tk();root.withdraw()
    args=argparse.Namespace(vision='baseline',policy=None,campus_config=None)
    app=Desktop(root,load_config({'duration_s':1,'camera':{'noise_sigma':0}}),args)
    try:
        root.update_idletasks()
        app.single();assert app.world.frame==1
        app.toggle();assert app.running
        app.toggle();assert not app.running and app.world.frame==1,'pause must not reset'
        app.mode.set('fixed');app.set_mode()
        assert app.world.c['target']['mode']=='fixed' and app.world.frame==0
        app.single();app.save();assert '结果已保存' in app.status.get()
        app.save_config();assert (PROJECT/'.local/configs/desktop.json').exists()
        original=app.world
        app.editor.delete('1.0','end');app.editor.insert('1.0','{"dt_s": 0}')
        assert not app.reset();assert app.world is original
        app.draw();root.update_idletasks()
        print('PASS: native Tk launch, render, step, pause/resume, mode/reset, save, invalid config and close (CPU only)')
    finally:app.close()


if __name__=='__main__':main()
