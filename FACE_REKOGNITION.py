import boto3
import io
from PIL import Image
import time
import picamera
import RPi.GPIO as GPIO
from pygame import mixer
import os

import serial

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import smtplib

from firebase import firebase
firebase = firebase.FirebaseApplication("https://face-recognition-aa50d.firebaseio.com/")
##import InvalidParameterException
import datetime
import time
import pigpio 

isLocked = False
#pi = pigpio.pi()
s3 = boto3.resource('s3')
polly = boto3.client('polly')
GPIO.setmode(GPIO.BCM)
GPIO.setup(4, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

rekognition = boto3.client('rekognition', region_name='eu-west-1')
dynamodb = boto3.client('dynamodb', region_name='eu-west-1')

name = "A new guest"

def send_email(): 
    fromaddr = "aashrav.shetty01@gmail.com"
    toaddr ="aashrav.shetty01@gmail.com"
     
    msg = MIMEMultipart()
     
    msg['From'] = fromaddr
    msg['To'] = toaddr
    msg['Subject'] = name + " is at the door"
     
    body = name + " is waiting at your front door. Photo of the guest is attached."
     
    msg.attach(MIMEText(body, 'plain'))
     
    filename = "sample.jpg"
    attachment = open("/home/pi/Desktop/guest.jpg", "rb")
     
    part = MIMEBase('application', 'octet-stream')
    part.set_payload((attachment).read())
    encoders.encode_base64(part)
    part.add_header('Content-Disposition', "attachment; filename= %s" % filename)
     
    msg.attach(part)
     
    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(fromaddr, "kuewexaashrav")
    text = msg.as_string()
    server.sendmail(fromaddr, toaddr, text) 
    server.quit()
    
while True:
    if GPIO.input(4):
        name = "A new guest"
        with picamera.PiCamera() as camera:
            camera.resolution = (1280,720)
            camera.capture("/home/pi/Desktop/guest" + ".jpg")
        image = Image.open("guest.jpg")
        stream = io.BytesIO()
        image.save(stream,format="JPEG")
        image_binary = stream.getvalue()
        
        try:
            response = rekognition.search_faces_by_image(
            CollectionId='guest_collection',
            Image={'Bytes':image_binary}                                       
            )
            matchFound = False
            for match in response['FaceMatches']:
                
                    
                face = dynamodb.get_item(
                    TableName='guest_collection',  
                    Key={'RekognitionId': {'S': match['Face']['FaceId']}}
                    )
                
                if 'Item' in face:
                    
                    
                    
                    name = face['Item']['FullName']['S']
                    ts = time.time()
                    
                    firebase.put("People", datetime.datetime.fromtimestamp(ts).strftime('%y-%m-%d %H:%M:%S'),name)
                    
                    print (face['Item']['FullName']['S'])
                    images=[('guest.jpg',face['Item']['FullName']['S'])]
                    
                    for image2 in images:
                        file = open(image2[0],'rb')
                        object = s3.Object('guest-images2','index/'+ image2[0])
                        ret = object.put(Body=file,  Metadata={'FullName':image2[1]}
                        )

                    matchFound = True
                    spoken_text = polly.synthesize_speech(Text=face['Item']['FullName']['S']+ " is at the door",OutputFormat = 'mp3',VoiceId = 'Emma')

                    
                    with open('output.mp3','wb') as f:
                        f.write(spoken_text['AudioStream'].read())
                        f.close()

                    mixer.init()
                    mixer.music.load("output.mp3")
                    mixer.music.play()
                    break
                
            
            if not matchFound:    
                print ('no match found in person lookup')
                spoken_text = polly.synthesize_speech(Text="A new guest is at the door",OutputFormat = 'mp3',VoiceId = 'Emma')

                with open('output.mp3','wb') as f:
                    f.write(spoken_text['AudioStream'].read())
                    f.close()

                mixer.init()
                mixer.music.load("output.mp3")
                mixer.music.play()
            

        except:
            print ("No faces detected")
            
            spoken_text = polly.synthesize_speech(Text="No faces detected",OutputFormat = 'mp3',VoiceId = 'Emma')

            with open('output.mp3','wb') as f:
                f.write(spoken_text['AudioStream'].read())
                f.close()

            mixer.init()
            mixer.music.load("output.mp3")
            mixer.music.play()
    if(isLocked == False and str(firebase.get("LockStatus",None)) == "True"):
##        print("Hi")
        pi.set_servo_pulsewidth(17, 800) ##LOCK
##        ser.flushInput()

        
        isLocked = True;
    elif(isLocked == True and str(firebase.get("LockStatus",None)) == "False"):
##        print("Bye");
        pi.set_servo_pulsewidth(17, 2000)
##        ser.flushInput()
        isLocked = False;
            
##        send_email()
        
        

        

