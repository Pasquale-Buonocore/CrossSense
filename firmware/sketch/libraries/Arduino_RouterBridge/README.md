Arduino_RouterBridge 0.4.3, MPL-2.0. Source: https://github.com/arduino-libraries/Arduino_RouterBridge/tree/0.4.3/src

Local modifications in bridge.h: RPC request buffer 1024 bytes (upstream default 256), worker stack 4096 bytes (upstream 500). This accommodates Bridge v1 JSON up to 900 bytes plus MsgPack envelope. All translation units use the same buffer setting. Keep this vendored source until upstream supports configuring the buffer consistently.
