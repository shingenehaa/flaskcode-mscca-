import cv2
from pyzbar.pyzbar import decode
from gtts import gTTS
import os
import datetime
import re
import pytesseract
import mysql.connector
from mysql.connector import Error

# Initialize barcode_data as a global variable
barcode_data = ""

def play_audio(text, lang="en"):
    try:
        tts = gTTS(text=text, lang=lang)
        tts.save("output.mp3")
        os.system("start output.mp3")
    except Exception as e:
        print("Text-to-speech error:", e)

def scan_barcodes(frame):
    global barcode_data
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    barcodes = decode(gray)
    
    for barcode in barcodes:
        barcode_data = barcode.data.decode('utf-8')
        barcode_type = barcode.type
        barcode_rect_points = barcode.polygon
        print(f"Barcode Type: {barcode_type}, Data: {barcode_data}")
        
        if barcode_rect_points:
            n = len(barcode_rect_points)
            for i in range(n):
                cv2.line(frame, barcode_rect_points[i], barcode_rect_points[(i+1) % n], (0, 255, 0), 3)

    return frame

# Webcam initialization
video_capture = cv2.VideoCapture(0)
barcode_detected = False

while not barcode_detected:
    ret, frame = video_capture.read()
    if ret:
        frame_with_barcodes = scan_barcodes(frame)
        cv2.imshow('Barcode Scanner', frame_with_barcodes)

        if len(decode(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY))) > 0:
            barcode_detected = True

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

video_capture.release()
cv2.destroyAllWindows()

print("Final Barcode Data:", barcode_data)

# Connect to the MySQL database
conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="mydatabase"
)
cursor = conn.cursor()

# Initialize plate cascade
plate_cascade_path = "C:\camnumplate\haskelchick.xml"
plate_cascade = cv2.CascadeClassifier(plate_cascade_path)

processed_vehicles = {}

# Capture video and process license plates
cap = cv2.VideoCapture(1)
while True:
    success, img = cap.read()

    # Convert the image to grayscale for license plate detection
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Detect license plates
    plates = plate_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(100, 30))

    for (x, y, w, h) in plates:
        # Extract the license plate region
        plate_region = gray[y:y + h, x:x + w]

         # Draw a green rectangle around the license plate region
        cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)

        # Use OCR to extract characters from the license plate
        plate_text = pytesseract.image_to_string(plate_region, config='--psm 7')

        # Clean up extracted text (remove whitespace, etc.)
        cleaned_plate_text = ''.join(plate_text.split())

        # Check if the cleaned_plate_text matches a number plate pattern
        plate_pattern = re.compile(r'^[A-Za-z]{2}\d{2}[A-Za-z]{2}\d{4}$')  # Adjust the pattern as needed
        if plate_pattern.match(cleaned_plate_text):
            # Check if the number plate has been processed today
            current_date = datetime.datetime.now().date()
            if cleaned_plate_text in processed_vehicles and processed_vehicles[cleaned_plate_text] == current_date:
                print(f"Vehicle {cleaned_plate_text} already processed today.")
                continue  # Skip further processing for this plate

            # Check if the number plate exists in the users table
            select_query = "SELECT vehicle_type, total_amt FROM users WHERE vehicle_number = %s"
            cursor.execute(select_query, (cleaned_plate_text,))
            result = cursor.fetchone()

            if result:
                vehicle_type = result[0]
                total_amt = result[1]

                # Deduct money and update the users table
                if vehicle_type == 'TwoWheeler':
                    total_amt -= 4
                elif vehicle_type == 'FourWheeler':
                    total_amt -= 10

                update_query = "UPDATE users SET total_amt = %s WHERE vehicle_number = %s"
                cursor.execute(update_query, (total_amt, cleaned_plate_text))
                conn.commit()

                # Insert data into the log_table
                insert_log_query = "INSERT INTO log_table (vehicle_number, entry_date, exit_date, vehicle_type) VALUES (%s, %s, %s, %s)"
                entry_date = datetime.datetime.now()
                exit_date = datetime.datetime.now()

                cursor.execute(insert_log_query, (cleaned_plate_text, entry_date, exit_date, vehicle_type))
                conn.commit()

                processed_vehicles[cleaned_plate_text] = current_date
                print(f"Vehicle {cleaned_plate_text} approved. Total amount updated to {total_amt}.")
            else:
                print(f"Vehicle {cleaned_plate_text} not found or not approved. Access denied.")

    # Create a named window with a GUI normal flag
    cv2.namedWindow("License Plate Detection", cv2.WINDOW_NORMAL | cv2.WINDOW_GUI_NORMAL)

    # Display the processed image in the named window
    cv2.imshow("License Plate Detection", img)

    # Break the loop when 'q' key is pressed
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Close MySQL connection
cursor.close()
conn.close()

# Release the video capture and close OpenCV windows
cap.release()
cv2.destroyAllWindows()