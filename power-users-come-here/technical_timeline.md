## Initial Investigation


* XInput mode provided analog triggers but rendered the L4 and R4 buttons unmappable (by software).


* DirectInput (DInput) mode allowed L4 and R4 to be mapped independently but caused the LT and RT triggers to register as digital buttons.


* I then searched for whether or not the DirectInput API natively supported analog triggers. Found out that it does.


* I used the tool `USBView` to obtain USB descriptors for the gamepad, identifying Vendor ID 2DC8 and Product ID 301C.


* I then used `hidapitester` via PowerShell to pull the report descriptor for the DInput interface.


* My initial hypothesis assumed the controller firmware was discarding the analog data before transmission.


## Raw Data Capture and Manual Decoding


* I utilized `hidapitester --read-input-forever` to capture raw 16-byte HID input reports.


* I executed specific inputs in isolation, such as trying to drag the left stick horizontally and slowly squeezing the triggers.


* By observing the raw hexadecimal output, I noticed that certain bytes always defaulted to 7F or 0F when centered.


* After a while of doing this, I successfully mapped the entire 16-byte report structure manually.


* Byte 1 functioned as a general button activity flag.


* Byte 2 contained standard face and shoulder buttons.


* Byte 3 contained special buttons like Start, Select, Home, stick clicks, and digital trigger states.


* Byte 4 represented the D-pad directional inputs.


* Bytes 5 through 8 contained the analog X and Y axes for both the left and right sticks.


* My original hypothesis was killed when I discovered Bytes 9 and 10 contained smooth, 0 to 255 analog data corresponding to the right and left triggers respectively. 


* The latter 6 bytes did not change at any point during testing, leading me to believe the gamepad only outputs 10 bytes of data per report.


* This discovery proved the controller firmware was transmitting the analog data, but the HID descriptor was failing to expose it to Windows properly. That's where this feature-crept project came to life.