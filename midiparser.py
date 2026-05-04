from copy import Error

class MidiParser:

    def __init__(self, filename):
        self.filename = filename
        self.tempo_map = []
        self.all_events = []
        self.ppqn_value = 0
        self.note_pairs = []
        
    def parse(self):
        with open(self.filename, "rb") as f:
            self.tempo_map = []
            all_notes = 0
            off_notes = 0
            active_notes = {}
            self.note_pairs = []
            self.all_events = []
            self.absolute_tick = 0
            self.running_status = None
            data = f.read()

            smf_format = data[8:10] # Read the SMF format, bytes 8 and 9, expected sizes are 0, 1, or 2
            smf_format_value = int.from_bytes(smf_format, byteorder="big")
            print("SMF Format:", smf_format_value)

            midi_tracks = data[10:12] # Read the number of MIDI tracks, bytes 10 and 11, expected sizes, 1-16
            midi_tracks_value = int.from_bytes(midi_tracks, byteorder="big")
            print("MIDI Tracks:", midi_tracks_value)

            self.ppqn = data[12:14] # Read the PPQN resolution, bytes 12 and 13, expected sizes 1-65535
            self.ppqn_value = int.from_bytes(self.ppqn, byteorder="big")
            print("PPQN Resolution:", self.ppqn_value)

            cursor = 14 # Start of the first track chunk
            for i in range(midi_tracks_value):
                if data[cursor:cursor+4] == b'MTrk':
                    self.absolute_tick = 0
                    self.running_status = None
                    print(f"Track {i+1} found at byte {cursor}")
                    p = 0
                    #track_data_start = cursor + 8
                    #print(f"First 10 bytes of data: {data[track_data_start : track_data_start + 10].hex(' ')}")
                    track_length = int.from_bytes(data[cursor+4:cursor+8], byteorder="big") # Reads the next 4 bytes after MTrk to get the track length in bytes (uint32)
                    print(f"Track {i+1} length: {track_length}")

                    track_data = data[cursor+8:cursor+8+track_length] # Reads the track data based on the track length
                
                    while p < len(track_data):

                        #print(f"DEBUG: Current p: {p}, Total length: {len(track_data)}")
                        #status = track_data[p]
                        delta = 0
                        while True:
                            byte = track_data[p]
                            p += 1
                            delta = (delta << 7) | (byte & 0x7F)
                            if byte < 0x80:
                                break                                                     
                        #print(f"Delta time: {delta}")
                        self.absolute_tick += delta

                        status = track_data[p] # Reads what kind of event it is
                        if status >= 0x80:
                            running_status = status
                            p += 1
                            if running_status < 0xF0:
                                running_status = status
                        elif status >= 0xFF:
                            # Meta events do not use running status, so we do not update it
                            p += 1
                        else:
                            status = running_status
                        if status is None:
                            raise Error("Missing status byte")
                        
                        #print(f"DEBUG: Status byte: {status:#02x} at position {p}")
                        #print(f"First meta event of track {i+1}: {status}")
                        #p += 1
                        
                        if 0x80 <= status <= 0xEF: # MIDI event
                            
                            command = status & 0xF0
                            channel = status & 0x0F
                            if command == 0x90: # Note on
                                note = track_data[p]
                                velocity = track_data[p+1]
                                #print(f"Note on: channel {channel}, note {note}, velocity {velocity}")
                                
                                if velocity > 0:
                                    active_notes[(channel, note)] = (self.absolute_tick, velocity)
                                    all_notes += 1
                                else:
                                    if (channel, note) in active_notes:
                                        start_tick, start_velocity = active_notes.pop((channel, note))
                                        self.note_pairs.append((start_tick, self.absolute_tick, channel, note, start_velocity))
                                    off_notes += 1
                                p += 2

                            if command == 0x80: # Note off
                                note = track_data[p]
                                velocity = track_data[p+1]
                                #print(f"Note off: channel {channel}, note {note}, velocity {velocity}")
                                if (channel, note) in active_notes:
                                        start_tick, start_velocity = active_notes.pop((channel, note))
                                        self.note_pairs.append((start_tick, self.absolute_tick, channel, note, start_velocity))
                                off_notes += 1
                                p += 2

                            if command == 0xB0: # Control change
                                controller = track_data[p]
                                value = track_data[p+1]
                                #print(f"Control change on channel {channel}: controller {controller}, value {value}")
                                p += 2

                            if command == 0xC0: # Program change
                                instrument = track_data[p]
                                #print(f"Program change on channel {channel}: instrument {instrument}")
                                p += 1
                            
                            if command == 0xD0: # Channel pressure
                                pressure = track_data[p]
                                #print(f"Channel pressure on channel {channel}: pressure {pressure}")
                                p += 1

                            if command == 0xE0: # Pitch bends
                                lsb = track_data[p]
                                msb = track_data[p+1]
                                pitch_bend_value = (msb << 7) | lsb
                                #print(f"Pitch bend on channel {channel}: value {pitch_bend_value - 8192}")
                                p += 2

                        elif status == 0xF0 or status == 0xF7: # SysEx event
                            sysex_length = 0
                            while True:
                                byte = track_data[p]
                                p += 1
                                sysex_length = (sysex_length << 7) | (byte & 0x7F)
                                if byte < 0x80:
                                    break
                            
                            #print(f"SysEx event of length {sysex_length} at position {p}")
                            p += sysex_length # Skip the SysEx event data for now, as we are only interested in the first meta event of each track

                        elif status == 0xFF: # Metadata
                            status_type = track_data[p]
                            #print(f"First meta event type of track {i+1}: {status_type}")
                            p += 1
                            status_length = track_data[p] # Reads how many bytes the metadata is
                            #print(f"First meta event length of track {i+1}: {status_length}")
                            p += 1

                            if status_type == 0x01: # Any text
                                len_text = track_data[p:p+status_length].decode("utf-8", errors="ignore")
                                #print(f"Text: {len_text}")
                                p += status_length

                            if status_type == 0x02: # Copyright
                                copyright_name = track_data[p:p+status_length].decode("utf-8", errors="ignore")
                                #print(f"Copyright: {copyright_name}")
                                p += status_length

                            if status_type == 0x03: # Track name
                                track_name = track_data[p:p+status_length].decode("utf-8", errors="ignore") # Reads the track name based on the length of the metadata
                                #print(f"Track {i+1} name: {track_name}")
                                p += status_length

                            if status_type == 0x04: # Instrument name
                                instrument_name = track_data[p:p+status_length].decode("utf-8", errors="ignore")
                                #print(f"Instrument name: {instrument_name}")
                                p += status_length

                            if status_type == 0x2F: # End of track
                                #print(f"End of track {i+1}")
                                #p += 1
                                break

                            if status_type == 0x51: # Tempo
                                tempo = int.from_bytes(track_data[p:p+3], byteorder="big") # Reads the tempo in microseconds per quarter note (uint24)
                                #print(f"Tempo: {60000000 / tempo}")
                                self.tempo_map.append((self.absolute_tick, tempo))
                                p += status_length

                            if status_type == 0x58: # Time signature
                                numerator = track_data[p]
                                denominator = track_data[p+1]
                                #print(f"Time signature: {numerator}/{2**denominator}")
                                p += status_length

                            if status_type == 0x59: # Key signature
                                key = track_data[p]
                                scale = track_data[p+1]
                                #print(f"Key signature: {key} sharps/flats, scale: {'major' if scale == 0 else 'minor'}")
                                p += status_length
                        else:
                            print(f"ALARM: Found unexpected byte {status} at pointer {p}")
                            p += status_length # Skip the event data for now, as we are only interested in the first meta event of each track
                    cursor += 8 + track_length

            #print("All notes:", all_notes)
            #print("Off notes:", off_notes)
            #print("Note pairs:", len(self.note_pairs))
            return self.sort_events()
    def sort_events(self):
        print("Sorting events...")
        for start_tick, end_tick, channel, note, velocity in self.note_pairs:
            self.all_events.append((start_tick, 0x90 | channel, note, velocity))
            self.all_events.append((end_tick, 0x80 | channel, note, 0))
        self.all_events.sort(key=lambda x: x[0]) # Sort events by their tick value
        print("All events:", len(self.all_events))
        return self.all_events, self.tempo_map, self.ppqn_value