import ctypes
#import kdmapi as kdm
import time
import midiparser as parser
kdm = ctypes.WinDLL("OmniMIDI.dll")
init = kdm.IsKDMAPIAvailable()

midi = parser.MidiParser("Avast Your Ass Black Final.mid")
events, tempo_map, ppqn = midi.parse()

print("Events:", len(events))
print("Tempo map:", tempo_map)
print("PPQN:", ppqn)

first_ten_events = events[:10]
for event in first_ten_events:
    print(event)

def ticks_to_seconds(ticks, ppqn, tempo_us):
    return (ticks / ppqn) * (tempo_us / 1000000)

def send_note(status, note, velocity):
    #status = 0x90 | (channel & 0x0F)

    data = status | (note << 8) | (velocity << 16)
    kdm.SendDirectData(data)
def send_note_off(status, note):
    #status = 0x80 | (channel & 0x0F)

    data = status | (note << 8)
    kdm.SendDirectData(data)

kdm.InitializeKDMAPIStream()
tempo_index = 0
last_tick = 0
for tick, status, note, velocity in events:
    if tempo_index + 1 < len(tempo_map):
        next_tempo_tick = tempo_map[tempo_index + 1][0]

        if tick >= next_tempo_tick:
            tempo_index += 1
            print(f"Tempo changed to {tempo_map[tempo_index][1]} at tick {tick}")

    current_tempo_us = tempo_map[tempo_index][1]

    delta = tick - last_tick
    #print("Wait", delta, "ticks before next event")
    
    wait_time = ticks_to_seconds(delta, ppqn, current_tempo_us)
    #print(wait_time)
    if wait_time > 0:
        time.sleep(wait_time)

    if status >= 0x90 and velocity > 0:
        send_note(status, note, velocity)
    elif status >= 0x80:
        send_note_off(status, note)
    
    last_tick = tick

kdm.TerminateKDMAPIStream()