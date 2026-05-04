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

def ticks_to_seconds(ticks, ppqn, tempo_us):
    return (ticks / ppqn) * (tempo_us / 1000000)

def seconds_per_tick(ppqn, tempo_us):
    return (tempo_us / 1000000) / ppqn

def send_note(status, note, velocity):
    #status = 0x90 | (channel & 0x0F)

    data = status | (note << 8) | (velocity << 16)
    kdm.SendDirectData(data)
def send_note_off(status, note):
    #status = 0x80 | (channel & 0x0F)

    data = status | (note << 8)
    kdm.SendDirectData(data)

kdm.InitializeKDMAPIStream()
current_midi_tick = 0
event_idx = 0
total_events = len(events)
tempo_index = 0
last_tick = 0
start_time = time.perf_counter()
#cumulative_time = 0.0

for tick, status, note, velocity in events:
    if tempo_index + 1 < len(tempo_map):
        if current_midi_tick >= tempo_map[tempo_index + 1][0]:
            tempo_index += 1
            print(f"Tempo changed to {tempo_map[tempo_index][1]} at tick {tick}")

    current_tempo_us = tempo_map[tempo_index][1]

    spt = seconds_per_tick(ppqn, current_tempo_us)

    current_tempo_us = tempo_map[tempo_index][1]

    target_time = current_midi_tick * spt

    while (time.perf_counter() - start_time) < target_time:
        pass
    while event_idx < total_events and events[event_idx][0] <= current_midi_tick:
        tick, status, note, velocity = events[event_idx]
        if status >= 0x90 and velocity > 0:
            send_note(status, note, velocity)
        elif status >= 0x80:
            send_note_off(status, note)
        event_idx += 1
    current_midi_tick = tick
    print(f"Current MIDI tick: {current_midi_tick} \r", end="", flush=True)
kdm.TerminateKDMAPIStream()