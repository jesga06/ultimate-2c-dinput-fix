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