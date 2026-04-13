with open("flourish.mid", "rb") as f:
    data = f.read()
    print(data[:25])

    smf_format = data[8:10] # Read the SMF format, bytes 8 and 9, expected sizes are 0, 1, or 2
    smf_format_value = int.from_bytes(smf_format, byteorder="big")
    print("SMF Format:", smf_format_value)

    midi_tracks = data[10:12] # Read the number of MIDI tracks, bytes 10 and 11, expected sizes, 1-16
    midi_tracks_value = int.from_bytes(midi_tracks, byteorder="big")
    print("MIDI Tracks:", midi_tracks_value)

    ppqn = data[12:14] # Read the PPQN resolution, bytes 12 and 13, expected sizes 24-65535
    ppqn_value = int.from_bytes(ppqn, byteorder="big")
    print("PPQN Resolution:", ppqn_value)

    cursor = 14 # Start of the first track chunk
    for i in range(1):
        if data[cursor:cursor+4] == b'MTrk':
            print(f"Track {i+1} found at byte {cursor}")
            p = 0
            #track_data_start = cursor + 8
            #print(f"First 10 bytes of data: {data[track_data_start : track_data_start + 10].hex(' ')}")
            track_length = int.from_bytes(data[cursor+4:cursor+8], byteorder="big") # Reads the next 4 bytes after MTrk to get the track length in bytes (uint32)
            print(f"Track {i+1} length: {track_length}")

            track_data = data[cursor+8:cursor+8+track_length] # Reads the track data based on the track length

            while p < len(track_data):
                delta = 0
                while True:
                    byte = track_data[p]
                    p += 1
                    delta = (delta << 7) | (byte & 0x7F)
                    if byte < 0x80:
                        break                                                     
                print(f"Delta time: {delta}")

                status = track_data[p] # Reads what kind of event it is
                print(f"First meta event of track {i+1}: {status}")
                p += 1
                
                if 0x80 <= status <= 0xEF: # MIDI event
                    command = status & 0xF0
                    channel = status & 0x0F
                    
                    if command == 0xC0:
                        instrument = track_data[p]
                        print(f"Program change on channel {channel}: instrument {instrument}")


                if status == 0xFF: # Metadata
                    status_type = track_data[p]
                    print(f"First meta event type of track {i+1}: {status_type}")
                    p += 1
                    status_length = track_data[p] # Reads how many bytes the metadata is
                    print(f"First meta event length of track {i+1}: {status_length}")
                    p += 1

                    if status_type == 0x01: # Any text
                        len_text = track_data[p:p+status_length].decode("utf-8", errors="ignore")
                        print(f"Text: {len_text}")
                        p += status_length

                    if status_type == 0x02: # Copyright
                        copyright_name = track_data[p:p+status_length].decode("utf-8", errors="ignore")
                        print(f"Copyright: {copyright_name}")
                        p += status_length

                    if status_type == 0x03: # Track name
                        track_name = track_data[p:p+status_length].decode("utf-8", errors="ignore") # Reads the track name based on the length of the metadata
                        print(f"Track {i+1} name: {track_name}")
                        p += status_length

                    if status_type == 0x04: # Instrument name
                        instrument_name = track_data[p:p+status_length].decode("utf-8", errors="ignore")
                        print(f"Instrument name: {instrument_name}")
                        p += status_length

                    if status_type == 0x2F: # End of track
                        print(f"End of track {i+1}")
                        break

                    if status_type == 0x51: # Tempo
                        tempo = int.from_bytes(track_data[p:p+3], byteorder="big") # Reads the tempo in microseconds per quarter note (uint24)
                        print(f"Tempo: {60000000 / tempo}")
                        p += status_length

                    if status_type == 0x58: # Time signature
                        numerator = track_data[p]
                        denominator = track_data[p+1]
                        print(f"Time signature: {numerator}/{2**denominator}")
                        p += status_length

                    if status_type == 0x59: # Key signature
                        key = track_data[p]
                        scale = track_data[p+1]
                        print(f"Key signature: {key} sharps/flats, scale: {'major' if scale == 0 else 'minor'}")
                        p += status_length
                #else:
                #    p += status_length # Skip the event data for now, as we are only interested in the first meta event of each track
            cursor += 8 + track_length
            