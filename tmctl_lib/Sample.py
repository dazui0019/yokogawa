#
# (c) Copyright 2025 Yokogawa Test & Measurement Corporation
#
# sub-system          :sample.py
# environment         :Python 3.11.4(64bit)
# sample program list :sampleSetTdiv
#                      sampleGetWaveform
#                      sampleGetMeasure
#                      sampleSaveWaveform
#                      sampleControlInstrument

import time
import tmctlLib

# Sample functions.

def sampleSetTdiv(tmctl,deviceID) :
  
  print("Execute setting Tdiv.\n")
  ret = tmctl.Send(deviceID,":TIMebase:TDIV 100ms")
  ret = tmctl.Send(deviceID,":TIMebase:TDIV?")
  ret, buf, length = tmctl.Receive(deviceID, 1000)						# 1000：Max recieve size(byte)
  
  return ret

def sampleGetMeasure(tmctl,deviceID) :
  
  print("Execute getting measure value.\n")
  ret = tmctl.Send(deviceID,":STOP")
  ret = tmctl.Send(deviceID,":COMMunicate:HEADer OFF")
  ret = tmctl.Send(deviceID,":MEASure:MODE OFF")
  ret = tmctl.Send(deviceID,":CHANnel:DISPlay ON")
  ret = tmctl.Send(deviceID,":CHANnel:PROBe 10")
  ret = tmctl.Send(deviceID,":CHANnel:VDIV 500mV")
  ret = tmctl.Send(deviceID,":ACQuire:MODE NORMal")
  ret = tmctl.Send(deviceID,":ACQuire:RLENgth 1250")
  ret = tmctl.Send(deviceID,":TIMebase:TDIV 100ms")
  ret = tmctl.Send(deviceID,":TRIGger:SIMPle:LEVel 500mV")
  ret = tmctl.Send(deviceID,":MEASure:CHANnel1:PTOPeak:STATe ON")
  ret = tmctl.Send(deviceID,":MEASure:CHANnel1:AVERage:STATe ON")
  ret = tmctl.Send(deviceID,":MEASure:CHANnel1:FREQuency:STATe ON")
  ret = tmctl.Send(deviceID,":MEASure:TRANge -5,5")
  ret = tmctl.Send(deviceID,":SSTart? 100")								# 100:Timeout value (in units of 100 ms)
  ret, buf, length = tmctl.Receive(deviceID, 1000)						# 1000：Max recieve size(byte)
  if 1 == int(buf) :
    print("Not triggered!")
    return ret
  ret = tmctl.Send(deviceID,":MEASure:MODE ON")							# The measure calculation begins
  ret = tmctl.Send(deviceID,":MEASure:WAIT? 100")						# 100:Timeout Value (in units of 100 ms)
  ret, buf, length = tmctl.Receive(deviceID, 1000)						# 1000：Max recieve size(byte)
  if 1 == int(buf) :
    print("Not finished measure!")
    return ret
  
  ret = tmctl.Send(deviceID,":MEASure:CHANnel1:PTOPeak:VALue?")
  ret, buf, length = tmctl.Receive(deviceID, 1000)						# 1000：Max recieve size(byte)
  print("Peak to peak value =", buf)
  
  ret = tmctl.Send(deviceID,":MEASure:CHANnel1:AVERage:VALue?")
  ret, buf, length = tmctl.Receive(deviceID, 1000)						# 1000：Max recieve size(byte)
  print("Average value =", buf)
  
  ret = tmctl.Send(deviceID,":MEASure:CHANnel1:FREQuency:VALue?")
  ret, buf, length = tmctl.Receive(deviceID, 1000)						# 1000：Max recieve size(byte)
  print("Frequency value =", buf)
  
  ret = tmctl.Send(deviceID,":COMMunicate:HEADer ON")
  
  return ret

def sampleGetWaveform(tmctl,deviceID) :
  
  vdv = 0																# V/div value
  ofs = 0																# Offset value
  div = 3200															# Division value
  
  print("Execute getting waveform.\n")
  ret = tmctl.Send(deviceID,":STOP")
  ret = tmctl.Send(deviceID,":COMMunicate:HEADer OFF")
  ret = tmctl.Send(deviceID,":WAVeform:TRACe 1")
  ret = tmctl.Send(deviceID,":WAVeform:RECord 0")
  ret = tmctl.Send(deviceID,":WAVeform:FORMat WORD")
  ret = tmctl.Send(deviceID,":WAVeform:BYTeorder LSBFirst")
  ret = tmctl.Send(deviceID,":WAVeform:STARt 0")
  ret = tmctl.Send(deviceID,":WAVeform:END 999")
  
  ret = tmctl.Send(deviceID,":WAVeform:RANGe?")
  ret, vdv, length = tmctl.Receive(deviceID, 1000)						# 1000：Max recieve size(byte)
  ret = tmctl.Send(deviceID,":WAVeform:OFFSet?")
  ret, ofs, length = tmctl.Receive(deviceID, 1000)						# 1000：Max recieve size(byte)
  ret = tmctl.Send(deviceID,":WAVeform:SEND?")
  ret, rlen = tmctl.ReceiveBlockHeader(deviceID)
  loopCount = int(rlen / 1000)											# Number of times to get 1000 bytes
  flacNum = rlen % 1000 + 1												# Fraction + terminator(LF)
  buf = bytearray(1000)
  
  for i in range(0,loopCount,1) :
    ret, rlen, endflag = tmctl.ReceiveBlockData(deviceID, buf, 1000)	# 1000：Max recieve size(byte)
    for j in range(0,int(rlen / 2),1) :									# Convert to physical values
      dat = (int.from_bytes( [buf[2*j] , buf[2*j+1]],byteorder = "little" , signed = True)) * (float(vdv) / div) + float(ofs)
      print(dat)
  
  ret, rlen, endflag = tmctl.ReceiveBlockData(deviceID, buf, flacNum)
  for k in range(0,int(rlen / 2),1) :									# Convert to physical values
    dat = (int.from_bytes( [buf[2*k] , buf[2*k+1]],byteorder = "little" , signed = True)) * (float(vdv) / div) + float(ofs)
    print(dat)
  
  ret = tmctl.Send(deviceID,":COMMunicate:HEADer ON")
  
  return ret

def sampleSaveWaveform(tmctl,deviceID) :

  print("Execute saving waveform.\n")
  
  ret = tmctl.Send(deviceID,":INITialize:EXECute")
  ret = tmctl.Send(deviceID,":CALibrate:EXECute")
  ret = tmctl.Send(deviceID,":ASETup:EXECute")
  
  while True :															# Wait for the auto setup to finish
    time.sleep(0.1)														# Wait 0.1[s]
    ret = tmctl.Send(deviceID,":STATus:CONDition?")
    ret, buf, length = tmctl.Receive(deviceID, 1000)					# 1000：Max recieve size(byte)
    if 1 == ( 1 & int(buf) ) :
      break
  
  time.sleep(2)															# Wait 2[s]
  ret = tmctl.Send(deviceID,":STOP")
  ret = tmctl.Send(deviceID,":COMMunicate:OVERlap 64")					# File operation allows to overlap
  ret = tmctl.Send(deviceID,"*CLS")
  ret = tmctl.Send(deviceID,":FILE:SAVE:ANAMing ON")
  ret = tmctl.Send(deviceID,":FILE:SAVE:NAME \"TEST\"")
  ret = tmctl.Send(deviceID,":FILE:SAVE:BINary:EXECute")
  
  while True :															# Wait for the waveform saving to finish
    time.sleep(0.1)														# Wait 0.1[s]
    ret = tmctl.Send(deviceID,":STATus:CONDition?")
    ret, buf, length = tmctl.Receive(deviceID, 1000)					# 1000：Max recieve size(byte)
    if 0 == ( 64 & int(buf) ) :
      break
  
  ret = tmctl.Send(deviceID,":COMMunicate:OVERlap 2400")				# Set default value
  return ret

def sampleControlInstrument(tmctl,deviceID) :
  
  vdv = 0																# V/div value
  ofs = 0																# Offset Value
  div = 3200															# Division Value
  
  ret = tmctl.Send(deviceID,":INITialize:EXECute")
  ret = tmctl.Send(deviceID,":CALibrate:EXECute")
  ret = tmctl.Send(deviceID,":COMMunicate:HEADer OFF")
  ret = tmctl.Send(deviceID,":ASETup:EXECute")
  
  while True :															# Wait for the auto setup to finish
    time.sleep(0.1)														# Wait 0.1[s]
    ret = tmctl.Send(deviceID,":STATus:CONDition?")
    ret, buf, length = tmctl.Receive(deviceID, 1000)					# 1000：Max recieve size(byte)
    if 1 == ( 1 & int(buf) ) :
      break
  
  # Execute SetTdiv
  ret = tmctl.Send(deviceID,":TIMebase:TDIV 100ms")
 
 
  # Execute GetMeasure
  ret = tmctl.Send(deviceID,":STOP")
  ret = tmctl.Send(deviceID,":MEASure:MODE OFF")
  ret = tmctl.Send(deviceID,":CHANnel:DISPlay ON")
  ret = tmctl.Send(deviceID,":CHANnel:PROBe 10")
  ret = tmctl.Send(deviceID,":CHANnel:VDIV 500mV")
  ret = tmctl.Send(deviceID,":ACQuire:MODE NORMal")
  ret = tmctl.Send(deviceID,":ACQuire:RLENgth 1250")
  ret = tmctl.Send(deviceID,":TRIGger:SIMPle:LEVel 500mV")
  ret = tmctl.Send(deviceID,":MEASure:CHANnel1:PTOPeak:STATe ON")
  ret = tmctl.Send(deviceID,":MEASure:CHANnel1:AVERage:STATe ON")
  ret = tmctl.Send(deviceID,":MEASure:CHANnel1:FREQuency:STATe ON")
  ret = tmctl.Send(deviceID,":MEASure:TRANge -5,5")
  ret = tmctl.Send(deviceID,":SSTart? 100")								# 100:Timeout value (in units of 100 ms)
  ret, buf, length = tmctl.Receive(deviceID, 1000)						# 1000：Max recieve size(byte)
  if 1 == int(buf) :
    print("Not triggered!")
    return ret
  ret = tmctl.Send(deviceID,":MEASure:MODE ON")							# The measure calculation begins
  ret = tmctl.Send(deviceID,":MEASure:WAIT? 100")						# 100:Timeout Value (in units of 100 ms)
  ret, buf, length = tmctl.Receive(deviceID, 1000)						# 1000：Max recieve size(byte)
  if 1 == int(buf) :
    print("Not finish measuring!")
    return ret
  
  ret = tmctl.Send(deviceID,":MEASure:CHANnel1:PTOPeak:VALue?")
  ret, buf, length = tmctl.Receive(deviceID, 1000)						# 1000：Max recieve size(byte)
  print("Peak to peak value =", buf)
  
  ret = tmctl.Send(deviceID,":MEASure:CHANnel1:AVERage:VALue?")
  ret, buf, length = tmctl.Receive(deviceID, 1000)						# 1000：Max recieve size(byte)
  print("Average value =", buf)
  
  ret = tmctl.Send(deviceID,":MEASure:CHANnel1:FREQuency:VALue?")
  ret, buf, length = tmctl.Receive(deviceID, 1000)						# 1000：Max recieve size(byte)
  print("Frequency value =", buf)
  
  
  # Execute GetWaveform
  ret = tmctl.Send(deviceID,":WAVeform:TRACe 1")
  ret = tmctl.Send(deviceID,":WAVeform:RECord 0")
  ret = tmctl.Send(deviceID,":WAVeform:FORMat WORD")
  ret = tmctl.Send(deviceID,":WAVeform:BYTeorder LSBFirst")
  ret = tmctl.Send(deviceID,":WAVeform:STARt 0")
  ret = tmctl.Send(deviceID,":WAVeform:END 999")
  
  ret = tmctl.Send(deviceID,":WAVeform:RANGe?")
  ret, vdv, length = tmctl.Receive(deviceID, 1000)						# 1000：Max recieve size(byte)
  ret = tmctl.Send(deviceID,":WAVeform:OFFSet?")
  ret, ofs, length = tmctl.Receive(deviceID, 1000)						# 1000：Max recieve size(byte)
  ret = tmctl.Send(deviceID,":WAVeform:SEND?")
  ret, rlen = tmctl.ReceiveBlockHeader(deviceID)
  loopCount = int(rlen / 1000)											# Number of times to get 1000 bytes
  flacNum = rlen % 1000 + 1												# Fraction + terminator
  buf = bytearray(1000)
  
  for i in range(0,loopCount,1) :
    ret, rlen, endflag = tmctl.ReceiveBlockData(deviceID, buf, 1000)	# 1000：Max recieve size(byte)
    for j in range(0,int(rlen / 2),1) :									# Convert to physical values
      dat = (int.from_bytes( [buf[2*j] , buf[2*j+1]],byteorder = "little" , signed = True)) * (float(vdv) / div) + float(ofs)
      print(dat)
  
  ret, rlen, endflag = tmctl.ReceiveBlockData(deviceID, buf, flacNum)
  for k in range(0,int(rlen / 2),1) :									# Convert to physical values
    dat = (int.from_bytes( [buf[2*k] , buf[2*k+1]],byteorder = "little" , signed = True)) * (float(vdv) / div) + float(ofs)
    print(dat)
  
  # Execute SaveWaveform
  ret = tmctl.Send(deviceID,":COMMunicate:OVERlap 64")					# File operation allows to overlap
  ret = tmctl.Send(deviceID,"*CLS")
  ret = tmctl.Send(deviceID,":FILE:SAVE:ANAMing ON")
  ret = tmctl.Send(deviceID,":FILE:SAVE:NAME \"TEST\"")
  ret = tmctl.Send(deviceID,":FILE:SAVE:BINary:EXECute")
  
  while True :															# Wait for the waveform saving to finish
    time.sleep(0.1)														# Wait 0.1[s]
    ret = tmctl.Send(deviceID,":STATus:CONDition?")
    ret, buf, length = tmctl.Receive(deviceID, 1000)					# 1000：Max recieve size(byte)
    if 0 == ( 64 & int(buf) ) :
      break
  
  ret = tmctl.Send(deviceID,":COMMunicate:HEADer ON")
  ret = tmctl.Send(deviceID,":COMMunicate:OVERlap 2400")				# Set default value
  return ret

if __name__ == '__main__' :
  
  tmctl = tmctlLib.TMCTL()
  
  # Connection Instrument
  
  # Please enable the I/F you will be using and enter the address
  # Default interface is USBTMC
  
  # Example : USBTMC Serial Number = 90Y701585
  ret, encode = tmctl.EncodeSerialNumber(128,"90Y701585")
  ret, deviceID = tmctl.Initialize(tmctlLib.TM_CTL_USBTMC3, encode)
  # Example : VXI-11 IP = 11.22.33.44
  # ret, deviceID = tmctl.Initialize(tmctlLib.TM_CTL_VXI11, "11.22.33.44")
  # Example : SOCKET IP = 11.22.33.44 , Port number = 12345
  # ret, deviceID = tmctl.Initialize(tmctlLib.TM_CTL_SOCKET, "11.22.33.44,12345")
  # Example : GPIB address = 1
  # ret, deviceID = tmctl.Initialize(tmctlLib.TM_CTL_GPIB, "1")
  
  ret = tmctl.SetTerm(deviceID, 2, 1)									# Sets the terminator LF for sending and receiving messages (use LF as the terminator for DLM series)
  ret = tmctl.SetTimeout(deviceID, 300)									# Sets the communication timeout value (in units of 100 ms)
  ret = tmctl.SetRen(deviceID, 1)										# Sets the device in remote or local mode (1:Remote control input)
  ret = tmctl.DeviceClear(deviceID)										# Clears the selected device
  
  print("Success connecting instrument.\n")
  
  # Execute sample
  
  # Please enable the sample to execute
  # Default sample is sampleUseInstrument
  
  # stat = sampleSetTdiv(tmctl,deviceID)
  # stat = sampleGetMeasure(tmctl,deviceID)
  # stat = sampleGetWaveform(tmctl,deviceID)
  # stat = sampleSaveWaveform(tmctl,deviceID)
  stat = sampleControlInstrument(tmctl,deviceID)
  
  if 0 == stat :
    print("Sample completed!")
  else :
    print("Sample error.")
  
  ret = tmctl.Send(deviceID,":STATus:ERRor?")
  ret, buf, length = tmctl.Receive(deviceID, 1000)
  print("Error condition：",buf)
  
  ret = tmctl.SetRen(deviceID, 0)
  ret = tmctl.Finish(deviceID)

