"""v0.3 speed frames only. Arm actions are an explicit simulator API, not wire extensions."""
import struct
import math

def crc(data, bits):
    value, poly = (255, 0x8c) if bits == 8 else (65535, 0x8408)
    for byte in data:
        value ^= byte
        for _ in range(8):
            value = (value >> 1) ^ poly if value & 1 else value >> 1
    return value

def encode_packet(command_id,payload,seq):
    if len(payload)>64: raise ValueError('payload exceeds protocol limit')
    head = struct.pack('<BHB', 0xa5, len(payload), seq%256)
    frame = head + bytes([crc(head, 8)]) + struct.pack('<H', command_id) + payload
    return frame + struct.pack('<H', crc(frame, 16))

def decode_packet(frame):
    if len(frame)<9 or frame[0]!=0xa5 or struct.unpack_from('<H',frame,1)[0]>64 or len(frame)!=struct.unpack_from('<H',frame,1)[0]+9:
        raise ValueError('invalid frame length')
    if crc(frame[:4],8) != frame[4] or crc(frame[:-2],16) != struct.unpack_from('<H',frame,len(frame)-2)[0]:
        raise ValueError('CRC mismatch')
    return struct.unpack_from('<H',frame,5)[0],frame[7:-2],frame[3]

def encode_speed(vx, vy, wz, enabled, seq, time_s):
    payload = struct.pack('<fffBH', vx, vy, wz, 0x15 if enabled else 0, int(time_s*1000)%65536)
    return encode_packet(1,payload,seq)

def decode_speed(frame):
    command,payload,_=decode_packet(frame)
    if command!=1 or len(payload)!=15:
        raise ValueError('not a speed frame')
    vx,vy,wz,flags,_ = struct.unpack('<fffBH',payload)
    if not all(math.isfinite(v) for v in (vx,vy,wz)): raise ValueError('non-finite wire velocity')
    return (0.,0.,0.) if flags & 8 or not flags & 4 else (vx,vy,wz)

def encode_velocity_feedback(vx,vy,wz,seq):
    def quantize(value,scale): return min(32767,max(-32768,round(value*scale)))
    return encode_packet(0x15,struct.pack('<hhh',quantize(vx,10000),quantize(vy,10000),quantize(wz,1000)),seq)
