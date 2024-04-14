import machine
import time
import os
#from machine import RTC

class TMP36:
    def __init__(self, pin, prevDay, rtc):
        self.tmp36= machine.ADC(pin)
        self.max_temp=-50
        self.num_of_meas=0
        self.sum_of_temp=0
        self.lastDaysLog=list()
        self.prevMeasurementDay=prevDay
        self.rtc=rtc
        try:
            os.remove("temperature_log.txt")
            os.remove("daily_temperature_log.txt")
            with open("temperature_log.txt", "a") as file:
                file.write("No day has passed since the start of the server.")
        except OSError:
            pass

    def getLastDaysLog(self):
        return self.lastDaysLog
    
    def MaxTempUpdate(self,temp):
        # Update max temp
        self.max_temp=max(self.max_temp,temp)

    def GetAvgTemp(self):
        if self.num_of_meas == 0:
            return 0
        return round(self.sum_of_temp/self.num_of_meas,2)
    
    def GetMaxTemp(self):
        return self.max_temp

    def read_temperature(self):
        adc_value=self.tmp36.read_u16()
        voltage =(3.3/65535)*adc_value # based on maximum output voltage and adc steps
        degC = (100*voltage)-50 # based on voltage to temperature diagramm
        degC=round(degC,1)
        self.MaxTempUpdate(degC)
        current_time = self.rtc.datetime()
        measurement_time = "{:02d}:{:02d}:{:02d}".format(current_time[4], current_time[5], current_time[6])  # Format: HH:MM:SS
        # Write temperature and time to a file
        with open("daily_temperature_log.txt", "a") as file:
            file.write(f"Temperature: {degC}°C, Time: {measurement_time}\n")
        return degC
    
    def RefreshDayLogFile(self):
        try:
            os.remove("temperature_log.txt")
        except OSError:
            pass
        with open("temperature_log.txt", "a") as file:
            for day, Avgtemp in self.lastDaysLog:
                file.write(f"Average temperature: {Avgtemp}°C, Day: {day}\n")

    def temperature_logging(self, measuredTemp):
        check_date=self.rtc.datetime()
        #temperorary=check_date[2]+1
        if self.prevMeasurementDay[0]!=check_date[2]:
            try:
                os.remove("daily_temperature_log.txt")
            except OSError:
                pass
            self.num_of_meas=1
            self.max_temp=-50
            self.sum_of_temp=measuredTemp
            self.lastDaysLog.append((str(self.prevMeasurementDay[0])+ "-" + str(self.prevMeasurementDay[1])+ "-" + str(self.prevMeasurementDay[2]), self.GetAvgTemp()))
            if len(self.lastDaysLog)==11:
                self.lastDaysLog.pop(0)
            self.RefreshDayLogFile()
            self.prevMeasurementDay=[check_date[2], check_date[1], check_date[0]]
        else:
            self.sum_of_temp+=measuredTemp
            self.num_of_meas+=1
