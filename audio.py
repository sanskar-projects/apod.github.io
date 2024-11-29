from PIL import Image
from sys import exit
import wave
import numpy as np

def hide_image(cover_path, secret_path, output_path):
    cover_image = Image.open(cover_path)
    secret_image = Image.open(secret_path)

    if cover_image.size[0] < secret_image.size[0] or cover_image.size[1] < secret_image.size[1]:
        raise ValueError("Cover image is too small to hold the secret image")

    cover_image = cover_image.convert("RGBA")
    secret_image = secret_image.convert("RGBA")

    cover_pixels = cover_image.load()
    secret_pixels = secret_image.load()

    for y in range(secret_image.size[1]):
        for x in range(secret_image.size[0]):
            cover_pixel = cover_pixels[x, y]
            secret_pixel = secret_pixels[x, y]

            new_pixel = (
                (cover_pixel[0] & 0xFE) | (secret_pixel[0] >> 7),
                (cover_pixel[1] & 0xFE) | (secret_pixel[1] >> 7),
                (cover_pixel[2] & 0xFE) | (secret_pixel[2] >> 7),
                cover_pixel[3]
            )

            cover_pixels[x, y] = new_pixel

    cover_image.save(output_path, "PNG")

def reveal_image(stego_image_path, output_path, size):
    stego_image = Image.open(stego_image_path)
    stego_image = stego_image.convert("RGBA")

    revealed_image = Image.new("RGBA", size)
    revealed_pixels = revealed_image.load()
    stego_pixels = stego_image.load()

    for y in range(size[1]):
        for x in range(size[0]):
            stego_pixel = stego_pixels[x, y]

            revealed_pixel = (
                (stego_pixel[0] & 1) << 7,
                (stego_pixel[1] & 1) << 7,
                (stego_pixel[2] & 1) << 7,
                255
            )

            revealed_pixels[x, y] = revealed_pixel

    revealed_image.save(output_path, "PNG")

def hide_text_in_image(cover_path, text, output_path):
    cover_image = Image.open(cover_path)
    cover_image = cover_image.convert("RGBA")
    cover_pixels = cover_image.load()

    text_binary = ''.join(format(ord(char), '08b') for char in text)
    text_len = len(text_binary)

    if cover_image.size[0] * cover_image.size[1] * 3 < text_len:
        raise ValueError("Cover image is too small to hold the secret text")

    index = 0
    for y in range(cover_image.size[1]):
        for x in range(cover_image.size[0]):
            cover_pixel = cover_pixels[x, y]

            if index < text_len:
                new_pixel = (
                    (cover_pixel[0] & 0xFE) | int(text_binary[index]),
                    cover_pixel[1],
                    cover_pixel[2],
                    cover_pixel[3]
                )
                index += 1
            else:
                new_pixel = cover_pixel

            if index < text_len:
                new_pixel = (
                    new_pixel[0],
                    (cover_pixel[1] & 0xFE) | int(text_binary[index]),
                    new_pixel[2],
                    new_pixel[3]
                )
                index += 1

            if index < text_len:
                new_pixel = (
                    new_pixel[0],
                    new_pixel[1],
                    (cover_pixel[2] & 0xFE) | int(text_binary[index]),
                    new_pixel[3]
                )
                index += 1

            cover_pixels[x, y] = new_pixel

    cover_image.save(output_path, "PNG")

def unhide_text_in_image(stego_image_path):
    stego_image = Image.open(stego_image_path)
    stego_image = stego_image.convert("RGBA")
    stego_pixels = stego_image.load()

    binary_data = ""
    for y in range(stego_image.size[1]):
        for x in range(stego_image.size[0]):
            stego_pixel = stego_pixels[x, y]
            binary_data += str(stego_pixel[0] & 1)
            binary_data += str(stego_pixel[1] & 1)
            binary_data += str(stego_pixel[2] & 1)

    all_bytes = [binary_data[i:i+8] for i in range(0, len(binary_data), 8)]
    decoded_text = ""
    for byte in all_bytes:
        decoded_text += chr(int(byte, 2))
        if decoded_text.endswith("###"):
            break

    if "###" in decoded_text:
        return decoded_text.rstrip("###")
    else:
        return ""

def get_image_dimensions(image_path):
    with Image.open(image_path) as img:
        width, height = img.size
        return width, height

def hide_audio(secret_audio, cover_audio, output_audio):
    """
    Hides a secret audio file within a cover audio file and saves the resulting file.

    Parameters:
        secret_audio (str): The file path of the secret audio file.
        cover_audio (str): The file path of the cover audio file.
        output_audio (str): The file path to save the new audio file with hidden data.
    """
    # Open the secret and cover audio files
    with wave.open(secret_audio, 'rb') as secret, wave.open(cover_audio, 'rb') as cover:
        # Read frames as bytes
        cover_frames = np.frombuffer(cover.readframes(cover.getnframes()), dtype=np.int16)
        secret_frames = np.frombuffer(secret.readframes(secret.getnframes()), dtype=np.int16)

        # Check if the cover audio can accommodate the secret audio
        required_samples = len(secret_frames) * 16  # Each secret sample requires 16 bits
        if required_samples > len(cover_frames):
            raise ValueError("Cover audio is too short to hide the secret audio.")

        # Encode the secret audio into the cover audio
        cover_frames = cover_frames.copy()  # Create a writable copy
        for i, sample in enumerate(secret_frames):
            for bit_index in range(16):  # Encode 16 bits of each sample
                bit = (sample >> bit_index) & 1  # Extract the bit
                cover_index = i * 16 + bit_index  # Calculate the index in cover frames
                cover_frames[cover_index] &= ~1  # Clear the least significant bit
                cover_frames[cover_index] |= bit  # Set the LSB with the secret bit

        # Save the new audio file with the hidden data
        with wave.open(output_audio, 'wb') as output:
            output.setparams(cover.getparams())
            output.writeframes(cover_frames.tobytes())

    print(f"Secret audio hidden in '{output_audio}'.")

    with wave.open(secret_audio, 'rb') as secret:
        secret_audio_length = secret.getnframes()
        print("Secret audio length",secret_audio_length)

def unhide_audio(cover_audio, output_secret_audio, secret_audio_length):
    """
    Unhides a secret audio file from a cover audio file and saves it.

    Parameters:
        cover_audio (str): The file path of the cover audio file.
        output_secret_audio (str): The file path to save the extracted secret audio file.
        secret_audio_length (int): The number of frames (samples) in the secret audio.
    """
    # Open the cover audio file
    with wave.open(cover_audio, 'rb') as cover:
        # Read frames as bytes
        cover_frames = np.frombuffer(cover.readframes(cover.getnframes()), dtype=np.int16)

        # Prepare to extract the secret audio
        secret_frames = np.zeros(secret_audio_length, dtype=np.int16)
        for i in range(secret_audio_length):
            for bit_index in range(16):  # Decode 16 bits per sample
                cover_index = i * 16 + bit_index  # Calculate the index in cover frames
                bit = cover_frames[cover_index] & 1  # Extract the least significant bit
                secret_frames[i] |= (bit << bit_index)  # Add the bit to the secret frame

        # Save the extracted secret audio
        with wave.open(output_secret_audio, 'wb') as output:
            params = cover.getparams()
            output.setparams((1, 2, params.framerate, secret_audio_length, 'NONE', 'not compressed'))
            output.writeframes(secret_frames.tobytes())

    print(f"Secret audio extracted to '{output_secret_audio}'.")

def hide_text_in_audio(secret_text, cover_audio, output_audio):
    """
    Hides a secret text message within a cover audio file and saves the resulting file.

    Parameters:
        secret_text (str): The secret text to hide.
        cover_audio (str): The file path of the cover audio file.
        output_audio (str): The file path to save the new audio file with hidden text.
    """
    # Convert the secret text to a binary representation
    secret_binary = ''.join(format(ord(char), '08b') for char in secret_text) + '00000000'  # Add a null terminator
    secret_bits = list(map(int, secret_binary))  # Convert binary string to list of bits

    # Open the cover audio file
    with wave.open(cover_audio, 'rb') as cover:
        # Read frames as bytes
        cover_frames = np.frombuffer(cover.readframes(cover.getnframes()), dtype=np.int16)

        # Check if the cover audio can accommodate the secret text
        if len(secret_bits) > len(cover_frames):
            raise ValueError("Cover audio is too short to hide the secret text.")

        # Create a writable copy of the cover frames
        modified_frames = cover_frames.copy()

        # Embed the secret bits into the least significant bits of the audio
        for i, bit in enumerate(secret_bits):
            modified_frames[i] &= ~1  # Clear the least significant bit
            modified_frames[i] |= bit  # Set the LSB with the secret bit

        # Save the modified audio with the hidden text
        with wave.open(output_audio, 'wb') as output:
            output.setparams(cover.getparams())
            output.writeframes(modified_frames.tobytes())

    print(f"Secret text hidden in '{output_audio}'.")

def unhide_text_from_audio(cover_audio):
    """
    Extracts a hidden text message from a cover audio file. 
    Returns an empty string if no hidden text is found.

    Parameters:
        cover_audio (str): The file path of the cover audio file containing the hidden text.

    Returns:
        str: The extracted secret text or an empty string if no text is found.
    """
    # Open the cover audio file
    with wave.open(cover_audio, 'rb') as cover:
        # Read frames as bytes
        cover_frames = np.frombuffer(cover.readframes(cover.getnframes()), dtype=np.int16)

        # Extract the least significant bits (LSBs) from the cover audio frames
        bits = []
        for frame in cover_frames:
            bits.append(frame & 1)  # Extract the LSB

        # Convert the extracted bits into bytes
        secret_binary = ''.join(map(str, bits))
        secret_bytes = [secret_binary[i:i + 8] for i in range(0, len(secret_binary), 8)]

        # Decode the bytes into characters, stopping at the null terminator (00000000)
        secret_text = ''
        for byte in secret_bytes:
            if byte == '00000000':  # Null terminator indicates the end of the hidden text
                break
            secret_text += chr(int(byte, 2))  # Convert binary to character

        # If no text was found, return an empty string
        if secret_text == '':
            return ''

    return secret_text

def main():
    print("-"*100)
    print("Choose an option:")
    print("1. Hide an image")
    print("2. Reveal an image")
    print("3. Hide text in image")
    print("4. Unhide hidden text in image")
    print("5. Hide an audio")
    print("6. Reveal an audio")
    print("7. Hide text in audio")
    print("8. Unhide hidden text in audio")
    print("9. Exit")
    choice = input("Enter your choice (1, 2, 3, 4, 5, 6, 7, 8, 9): ")
    if choice == "1":
        cover_path = input("Enter the path to the cover image: ")
        secret_path = input("Enter the path to the secret image: ")
        output_path = input("Enter the path to save the output image: ")
        hide_image(cover_path, secret_path, output_path)
        print("Image hiding process complete.")
    elif choice == "2":
        stego_image_path = input("Enter the path to the stego image: ")
        output_path = input("Enter the path to save the revealed image: ")
        width, height = get_image_dimensions(stego_image_path)
        reveal_image(stego_image_path, output_path, (width, height))
        print("Image revealing process complete.")
    elif choice == "3":
        cover_path = input("Enter the path to the cover image: ")
        text = input("Enter the text to hide: ") + "###"  # Adding delimiter to indicate end of hidden text
        output_path = input("Enter the path to save the output image: ")
        hide_text_in_image(cover_path, text, output_path)
        print("Text hiding process complete.")
    elif choice == "4":
        stego_image_path = input("Enter the path to the stego image: ")
        hidden_text = unhide_text_in_image(stego_image_path)
        if(hidden_text!=""):
            print(f"Hidden text: {hidden_text}")
        else:
            print("No hidden text found.")
    elif choice == "5":
        cover_audio = input("Enter the path to the cover audio: ")
        secret_audio = input("Enter the path to the secret audio: ")
        output_audio = input("Enter the path to save the output audio: ")
        hide_audio(secret_audio, cover_audio, output_audio)
        print("Audio hiding process complete.")
    elif choice == "6":
        cover_audio = input("Enter the path to the stego audio: ")
        output_secret_audio = input("Enter the path to save the revealed audio: ")
        secret_audio_length=int(input("Enter the secret audio length: "))
        unhide_audio(cover_audio, output_secret_audio, secret_audio_length)
        print("Audio revealing process complete.")
    elif choice == "7":
        cover_audio = input("Enter the path to the cover audio: ")
        secret_text = input("Enter the text to hide: ")
        output_audio = input("Enter the path to save the output audio: ")
        hide_text_in_audio(secret_text, cover_audio, output_audio)
        print("Text hiding process complete.")
    elif choice == "8":
        cover_audio = input("Enter the path to the stego audio: ")
        hidden_text = unhide_text_from_audio(cover_audio)
        if(hidden_text!=""):
            print(f"Hidden text: {hidden_text}")
        else:
            print("No hidden text found.")
    elif choice == "9":
        exit(0)
    else:
        print("Invalid choice.")

while True:
    main()
