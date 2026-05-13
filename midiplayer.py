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

track_colors = [
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




midi = parser.MidiParser("Black Rose Apostle.mid")
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
    for tick, status, note, velocity, track_id in events:
        
        channel  = status & 0x0F
        key = (track_id, channel, note)
        
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
                "velocity": velocity,
                "track_id": track_id
            }
            send_note(status, note, velocity)
            state['notes'] += 1
        elif status >= 0x80 or (status >= 0x90 and velocity == 0):
            state['active_notes'].pop(key, None)
            send_note_off(status, note)
        #event_idx += 1

        last_tick = tick
    state['running'] = False


note_width = WIDTH / 128
note_length_key = HEIGHT / 16
hit_line = HEIGHT / 1.15
pixels_per_tick = 10
active_starts = {}
render_notes = []
for tick, status, note, velocity, track_id in events:
    channel = status & 0x0F
    key = (track_id, channel, note)
    if status >= 0x90 and velocity > 0:
        active_starts[key] = tick
    elif status >= 0x80 or (status >= 0x90 and velocity == 0):
        if key in active_starts:
            start_tick = active_starts.pop(key)
            '''falling_notes.append({
                "start_tick": start_tick,
                "end_tick": tick,
                "channel": channel,
                "note": note,
                "velocity": velocity,
                "track_id": track_id
            })'''

            render_notes.append({
                "start_tick": start_tick,
                "end_tick": tick,
                "channel": channel,
                "note": note,
                "track_id": track_id,
                "x": note * note_width,
                "height": (tick - start_tick) * pixels_per_tick,
                "color": track_colors[track_id % len(track_colors)]
                })

kdm.InitializeKDMAPIStream()
current_midi_tick = 0
event_idx = 0
total_events = len(events)
notes = 0
start_time = time.perf_counter()
tempo_index = 0 
note_index = 0
margin = ppqn * 4
lookahead = ppqn * 8
#cumulative_time = 0.0

information_thread = threading.Thread(target=info, args=(state,), daemon=True)
information_thread.start()

playback_thread = threading.Thread(target=play_midi, args=(events, tempo_map, ppqn, state), daemon=True)
playback_thread.start()
render_mode = "falling"  # or "key", do whichever you want
last_render_tempo_index = -1
cached_spt = seconds_per_tick(ppqn, tempo_map[0][1])
try:
    while state["running"]:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                state['running'] = False
                break
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    if render_mode == "key":
                        render_mode = "falling"
                    elif render_mode == "falling":
                        render_mode = "key"
        screen.fill((20, 25, 23))
        note_snapshot = state['active_notes'].copy()
        

        if render_mode == "key":
            for (track_id, channel, note), note_info in note_snapshot.items():
                track_id = note_info['track_id']
                color = track_colors[track_id % len(track_colors)]
                note_position = note * note_width
                rect = pygame.Rect(note_position, state["note_channelposition"](channel), note_width, note_length_key)
                pygame.draw.rect(screen, color, rect)
        elif render_mode == "falling":


            if tempo_index + 1 < len(tempo_map):
                if state['current_midi_tick'] >= tempo_map[tempo_index + 1][0]:
                    tempo_index += 1

                
            pygame.draw.line(screen, (255, 255, 255), (0, hit_line), (WIDTH, hit_line), 2)
            elapsed_seconds = time.perf_counter() - start_time
            if tempo_index != last_render_tempo_index:
                cached_spt = seconds_per_tick(ppqn, tempo_map[tempo_index][1])
                last_render_tempo_index = tempo_index

            while note_index < len(render_notes) and render_notes[note_index]['end_tick'] < visual_tick:
                note_index += 1

            for i in range(note_index, len(render_notes)):
                note_data = render_notes[i]

                if note_data['start_tick'] > visual_tick + margin:
                    break

                duration_ticks = note_data["end_tick"] - note_data["start_tick"]
                ticks_until_hit = note_data["start_tick"] - visual_tick
                visual_tick = elapsed_seconds / cached_spt
                y = hit_line - ticks_until_hit * pixels_per_tick
                bottom_y = note_data["height"]
                rect = pygame.Rect(note_data["x"], y, note_width, note_data["height"])
                if bottom_y >= -100 and y <= HEIGHT + 200:
                    pygame.draw.rect(screen, note_data["color"], rect)
                
        pygame.display.flip()
        clock.tick(165)
        
        
finally:
    if not playback_thread.is_alive():
        print("\nPlayback finished! Waiting for 5 seconds before terminating the stream...")
        time.sleep(5)
        kdm.TerminateKDMAPIStream()
        state['running'] = False
        pygame.quit()