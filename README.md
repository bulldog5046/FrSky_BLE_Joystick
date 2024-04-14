## FrSKY Bluetooth Joystick Proof-of-Concept

Some code I threw together to show that FrSKY transmitters can be directly used as a joystick input over bluetooth without the need for an additional dongle.

The interface makes use of the trainer function which uses bluetooth. Tx should be set to the slave device so the interface can connect and subscribe to the update notifications.

Not intended to be used as-is but welcome anyone who wants to use the concept to create a interface.