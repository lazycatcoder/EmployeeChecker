import cv2
import face_recognition
import pymongo
import concurrent.futures
import datetime
import time
import os 
import json


def recognize_employee(image):
    # Connect to MongoDB and select the database and collection
    client = pymongo.MongoClient("mongodb://localhost:27017/")
    db = client["employee_check"]
    employees_collection = db["employee"]
    
    # Use face_recognition library to locate faces in the image
    face_locations = face_recognition.face_locations(image)

    # If no faces are detected, return None
    if len(face_locations) == 0:
        # Close MongoDB connection
        client.close()
        return None
    
    # Loop through known employees in the database and add their encodings and names to separate lists
    known_faces = []
    known_names = []
    for employee in employees_collection.find({}, {"_id": 0, "last_name": 1, "face_encoding": 1}):
        known_faces.append(json.loads(employee['face_encoding']))
        known_names.append(employee['last_name'])
    
    # Loop through the face encodings detected in the image and compare them to the known encodings
    for face_encoding in face_recognition.face_encodings(image, face_locations):
        matches = face_recognition.compare_faces(known_faces, face_encoding)      
        # If a match is found, return the employee's name
        if True in matches:
            match_index = matches.index(True)
            name = known_names[match_index]
            # Close MongoDB connection
            client.close()
            return name
        
    # Close MongoDB connection
    client.close()
    # If no matches are found, return None
    return None


def load_known_faces():
    # Connect to MongoDB and select the database and collection
    client = pymongo.MongoClient("mongodb://localhost:27017/")
    db = client["employee_check"]
    employees_collection = db["employee"]

    # Check if "employee" folder exists and is not empty
    if not os.path.isdir('employee') or not os.listdir('employee'):
        print('Folder "employee" is empty or does not exist. Skipping loading known faces.')
        # Close MongoDB connection
        client.close()
        return
    
    # Clear existing employee records in MongoDB collection
    employees_collection.delete_many({})
    
    # Loop through images in "employee" folder
    for filename in os.listdir('employee'):
        if filename.endswith('.jpg') or filename.endswith('.png'):
            # Extract name from file name
            name = os.path.splitext(filename)[0]
            if employees_collection.find_one({"last_name": name}):
                continue
            try:
                # Load image file and extract face encoding
                image = face_recognition.load_image_file(os.path.join('employee', filename))
                face_encodings = face_recognition.face_encodings(image)

                # Check if face was found in image
                if not face_encodings:
                    print(f"No faces found in image {filename}")
                    continue

                # Convert face encoding to list and insert employee record into MongoDB collection
                face_encoding = face_encodings[0].tolist()
                employees_collection.insert_one({"last_name": name, "face_encoding": json.dumps(face_encoding)})

            except Exception as e:
                # Handle errors when loading image files
                print(f'Error loading image "{filename}": {e}')

    # Close MongoDB connection
    client.close()


def draw_box(image, face_location, name):
    # Unpack the face_location tuple to get the coordinates of the detected face
    top, right, bottom, left = face_location
    if name is not None:
        cv2.rectangle(image, (left, top), (right, bottom), (0, 255, 0), 2)
    else:
        cv2.rectangle(image, (left, top), (right, bottom), (0, 0, 255), 2)
    
    # Label the detected face with the given name or "Unknown"
    if name is not None:
        cv2.putText(image, name, (left + 6, bottom - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
    else:
        cv2.putText(image, "Unknown", (left + 6, bottom - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
    return image


def arrival_time(last_name):
    # Connect to MongoDB and select the database and collection
    client = pymongo.MongoClient("mongodb://localhost:27017/")
    db = client["employee_check"]
    arrival_collection = db["arrival"]

    # Check if employee has a recent arrival record
    now = datetime.datetime.now()
    two_minutes_ago = now - datetime.timedelta(minutes=2)

    # Query MongoDB for an arrival record for this employee in the last two minutes
    result = arrival_collection.find_one({
        "employee_lastname": last_name, 
        "timestamp": {"$gt": two_minutes_ago.strftime('%H:%M:%S')}
    })

    if result is not None:
        # Recent arrival record exists, so return without adding a new one
        print(f"{last_name} has already checked in recently")
        # Close MongoDB connection
        client.close()
        return
    
    # Get employee ID and insert arrival record
    employee = db.employee.find_one({'last_name': last_name})
    
    # Employee found, so insert a new arrival record
    if employee is not None:
        employee_id = employee['_id']
        datestamp = now.strftime('%Y-%m-%d')
        timestamp = now.strftime('%H:%M:%S')
        arrival_data = {
            'employee_lastname': last_name,
            'employee_id': employee_id,
            'datestamp': datestamp,
            'timestamp': timestamp
        }
        db.arrival.insert_one(arrival_data)
        print(f"{last_name} has checked in at {timestamp}")
    else:
        # No employee found, so print an error message
        print(f"No employee found with last name {last_name}")

    # Close MongoDB connection
    client.close()


def process_face(image):
    # Record the start time for this face processing
    start_time = time.time()

    # Get the face locations in the image using the face_recognition library
    face_locations = face_recognition.face_locations(image)
    
    # Use a thread pool executor to parallelize face processing
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = []
        # Loop through each face location and process it
        for face_location in face_locations:
            top, right, bottom, left = face_location
            face_image = image[top:bottom, left:right]
            name = recognize_employee(face_image)
            elapsed_time = time.time() - start_time
            # If the elapsed time is less than 1 second, try recognizing the employee on a resized image
            if elapsed_time < 1:
                resized_image = cv2.resize(face_image, (0, 0), fx=0.25, fy=0.25)
                name = recognize_employee(resized_image)
                # If a name is recognized, submit arrival_time and draw_box functions to executor
                if name is not None:
                    future = executor.submit(arrival_time, name)
                    futures.append(future)
                    future = executor.submit(draw_box, image, face_location, name)
                    futures.append(future)
                # If no name is recognized, submit draw_box function with None as the name to executor
                else:
                    future = executor.submit(draw_box, image, face_location, None)
                    futures.append(future)

            # If the elapsed time is 1 second or more and a name is recognized, submit arrival_time and draw_box functions to executor
            elif name is not None:
                future = executor.submit(draw_box, image, face_location, name)
                futures.append(future)
                future = executor.submit(arrival_time, name)
                futures.append(future)

            # If the elapsed time is 1 second or more and no name is recognized, submit draw_box function with None as the name to executor
            else:
                future = executor.submit(draw_box, image, face_location, None)
                futures.append(future)

        # Check and cancel futures that take too long to complete
        start_time = time.time()
        for future in concurrent.futures.as_completed(futures, timeout=5):
            elapsed_time = time.time() - start_time
            if elapsed_time >= 5:
                future.cancel()

        # Wait for all futures to complete
        for future in concurrent.futures.as_completed(futures):
            pass


def run_camera():
    # Initialize the video capture object to capture video from the default camera 
    video_capture = cv2.VideoCapture("http://192.168.0.101:8080/video")  # Enter your URL of the IP camera
   
    # You can use your laptop's webcam to test
    # video_capture = cv2.VideoCapture(0) 
     
    while True:
        # Read a frame from the video capture object
        ret, frame = video_capture.read()     
        # If reading the frame fails, exit the loop
        if not ret:
            print('Failed to get frame from camera.')
            break
        # Process the face in the frame
        process_face(frame)
        # Show the frame in a window titled 'Video'
        cv2.imshow('Video', frame)
        # If the user presses the 'q' key, exit the loop
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Release the video capture object and destroy all windows
    video_capture.release()
    cv2.destroyAllWindows()


if __name__ == '__main__':
    load_known_faces()
    run_camera()