import pygame
import random
import ctypes
import threading
#import kdmapi as kdm
import time
import midiparser as parser
kdm = ctypes.WinDLL("OmniMIDI.dll")
init = kdm.IsKDMAPIAvailable()
channel_colors = [
    (255, 0, 0, 255),
    (255, 60, 0, 255),
    (255, 127, 0, 255),
    (255, 255, 0, 255),
    (127, 255, 0, 255),
    (60, 255, 0, 255),
    (0, 255, 0, 255),
    (0, 255, 127, 255),
    (0, 255, 255, 255),
    (0, 127, 255, 255),
    (0, 60, 255, 255),
    (0, 0, 255, 255),
    (127, 0, 255, 255),
    (255, 0, 255, 255),
    (255, 0, 127, 255),
    (255, 0, 60, 255)
]
WIDTH, HEIGHT = 800, 600
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.Clock()




midi = parser.MidiParser("Shanghai Teahouse~Chinese Tea V1s.mid")
events, tempo_map, ppqn = midi.parse()

print("Events:", len(events))
print("Tempo map:", tempo_map)
print("PPQN:", ppqn)



state = {
    "active_notes": {},
    "current_midi_tick": 0,
    "notes": 0,
    "running": True,
    "note_channelposition": lambda channel: channel * (HEIGHT / 16)
}


def info(shared_state):
    while shared_state['running']:
        print(f"Current MIDI tick: {shared_state['current_midi_tick']} | Notes: {shared_state['notes']} \r", end="", flush=True)
        #time.sleep(1)

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

def play_midi(events, tempo_map, ppqn, state):
    last_tick = 0
    cumulative_time = 0.0
    tempo_index = 0
    start_time = time.perf_counter()
    for tick, status, note, velocity in events:
        
        channel  = status & 0x0F
        key = (channel, note)
        
        state['current_midi_tick'] = tick
        if tempo_index + 1 < len(tempo_map):
            if state['current_midi_tick'] >= tempo_map[tempo_index + 1][0]:
                tempo_index += 1
                print(f"Tempo changed to {tempo_map[tempo_index][1]} at tick {tick}")
        

        delta_ticks = tick - last_tick
        current_tempo_us = tempo_map[tempo_index][1]

        spt = seconds_per_tick(ppqn, current_tempo_us)

        current_tempo_us = tempo_map[tempo_index][1]

        cumulative_time += delta_ticks * spt

        while (time.perf_counter() - start_time) < cumulative_time:
            if not state['running']: return
            pass
        #while event_idx < total_events and events[event_idx][0] <= state['current_midi_tick'] :
        #    tick, status, note, velocity = events[event_idx]
        if status >= 0x90 and velocity > 0:
            state['active_notes'][key] = {
                "start_tick": tick,
                "velocity": velocity
            }
            send_note(status, note, velocity)
            state['notes'] += 1
        elif status >= 0x80 or (status >= 0x90 and velocity == 0):
            state['active_notes'].pop(key, None)
            send_note_off(status, note)
        #event_idx += 1

        last_tick = tick
    state['running'] = False

        


kdm.InitializeKDMAPIStream()
current_midi_tick = 0
event_idx = 0
total_events = len(events)
notes = 0

#cumulative_time = 0.0

information_thread = threading.Thread(target=info, args=(state,), daemon=True)
information_thread.start()

playback_thread = threading.Thread(target=play_midi, args=(events, tempo_map, ppqn, state), daemon=True)
playback_thread.start()
try:
    while state["running"]:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                state['running'] = False
                break
        screen.fill((20, 25, 23))
        note_snapshot = state['active_notes'].copy()
        for (channel, note), note_info in note_snapshot.items():
            
            color = channel_colors[channel]
            note_width = WIDTH / 128
            note_length = HEIGHT / 16
            note_position = note * note_width
            rect = pygame.Rect(note_position, state["note_channelposition"](channel), note_width, note_length)
            
            pygame.draw.rect(screen, color, rect)
        pygame.display.flip()
        clock.tick(60)
        
        
finally:
    if not playback_thread.is_alive():
        print("\nPlayback finished! Waiting for 5 seconds before terminating the stream...")
        time.sleep(5)
        kdm.TerminateKDMAPIStream()
        state['running'] = False
        pygame.quit()