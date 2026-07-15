# small proof of concept i wrote up in a few mins to make sure i wasn't going crazy.

VID = 0x2DC8
PID = 0x301C

import pywinusb.hid as hid  

devices = hid.HidDeviceFilter(vendor_id=VID, product_id=PID).get_devices()

for d in devices:
    print("Device:")
    print("- Product:", d.product_name)
    print("- Vendor:", hex(d.vendor_id))
    print("- Product ID:", hex(d.product_id))
    print()

devices = hid.HidDeviceFilter(
    vendor_id=0x2DC8,
    product_id=0x301C
).get_devices()

device = devices[0]
device.open()
print("connected")

def sample_handler(data):
    print(
        "ID:", data[0],
        " | ",
        " ".join(f"{x:02X}" for x in data[1:])
    )

device.set_raw_data_handler(sample_handler)

while True:
    pass