from bleak import BleakClient, BleakScanner, BLEDevice
from bleak import BleakGATTCharacteristic
import asyncio
import binascii
import vgamepad as vg
import datetime
import struct

CHANNEL_COUNT = 8
PPM_MIN = 980
PPM_MAX = 2020
PPM_RANGE = PPM_MAX - PPM_MIN
HID_RANGE = 65535

gamepad = vg.VX360Gamepad()

def log_data(data: bytearray):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    hex_data = binascii.hexlify(data).decode('utf-8')
    with open("controller_data_log.txt", "a") as file:
        file.write(f"{timestamp}: {hex_data}\n")
        
def hasBoundaryMarkers(data: bytearray):
    return data[0] == 0x7e and data[-1] == 0x7e

def isCorrectFrameType(data: bytearray):
    return data[1] == 0x80

def getChecksum(data: bytearray):
    return data[-2]

def passesChecksum(checksum: int, data: bytearray):
    calculated_checksum = 0
    for i in range(len(data) - 1):
        calculated_checksum ^= data[i]
    return calculated_checksum == checksum, calculated_checksum

def unescape(data: bytearray):
    unescapedData = bytearray()
    i = 0
    while i < len(data):
        byte = data[i]
        
        if byte != 0x7d:
            unescapedData.append(byte)
        else:
            i += 1 
            if data[i] == 0x5e:
                unescapedData.append(0x7e)
            elif data[i] == 0x5d:
                unescapedData.append(0x7d)
            else:
                print("Unexpected escape sequence")
                return None
        i += 1
    
    return unescapedData

def parsePPMChannelData(data: bytearray):
    channels = [0,0,0,0,0,0,0,0]
    i = 1
    channel = 0
    for j in range(int(CHANNEL_COUNT/2)):
        channels[channel] = data[i] + ((data[i+1] & 0xf0) << 4) - 1500
        channels[channel+1] = ((data[i+1] & 0x0f) << 4) + ((data[i+2] & 0xf0) >> 4) + ((data[i+2] & 0x0f) << 8) - 1500

        channel+=2
        i+=3

    return channels

async def onUpdate(sender: BleakGATTCharacteristic, data: bytearray):
    log_data(data)
    
    if not hasBoundaryMarkers(data):
        print("Data does not have boundary markers.")
        return

    if not isCorrectFrameType(data):
        print("Incorrect frame type.")
        return

    unescapedData = unescape(data[1:-1])  # Excluding the initial and final boundary markers for unescaping
    if unescapedData is None:
        print("Failed to unescape data.")
        return

    checksum = getChecksum(data)
    valid_checksum, calculated_checksum = passesChecksum(checksum, unescapedData)

    if not valid_checksum:
        print("Failed checksum!")
        return
    
    channelData = parsePPMChannelData(unescapedData)
    #print(channelData)
    
    gamepad.left_joystick_float(x_value_float=(channelData[1] + 512) / 1024, y_value_float=(channelData[0] + 512) / 1024)  # values between -32768 and 32767
    gamepad.right_joystick_float(x_value_float=(channelData[2] + 512) / 1024, y_value_float=(channelData[3] + 512) / 1024)  # values between -32768 and 32767
    gamepad.right_trigger_float((channelData[4] + 512) / 1024)
    gamepad.press_button(vg.XUSB_BUTTON.XUSB_GAMEPAD_X) if channelData[5] >=0 else gamepad.release_button(vg.XUSB_BUTTON.XUSB_GAMEPAD_X)
    gamepad.update()

async def main():
    async with BleakClient("D0:2E:AB:8A:B9:A7") as client:
        try:
            if not client.is_connected:
                await client.connect()
            
            name = await client.read_gatt_char(2)
            print(f"Connected to {name}")
            
            await client.start_notify(42, onUpdate)
            
            while True:
                await asyncio.sleep(1)
        except Exception as e:
            print(f"Error: {e}")
            await client.disconnect()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Program terminated by user")
