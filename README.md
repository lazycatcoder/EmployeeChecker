<div align="center">
  <h1>Employee Checker</h1>
</div>

<div align="justify">

   This Python code implements a facial recognition system for employee check-in. The program uses [*OpenCV*](https://github.com/opencv/opencv-python) (cv2) library for image processing and [*Face Recognition*](https://github.com/ageitgey/face_recognition) library to recognize faces, compares them to a database of known employees, and returns the employee's name if a match is found. The program also keeps track of employee arrivals by adding a timestamp to the [*MongoDB*](https://www.mongodb.com) collection.

   <br>

   The main practical application of this code is tracking the presence of employees in the workplace. The code can be used to automatically register the entrance and exit of employees, as well as to monitor who is in the building at the moment, etc.

</div>

<br>



<div align="center">

   # Settings

</div>

<div align="left">

1. Clone this repository

```
   git clone https://github.com/lazycatcoder/EmployeeChecker.git
```


2. Install dependencies
   
```
   pip install -r requirements.txt
```

  🔴 *to install MongoDB, go to the official website: https://www.mongodb.com/*

3. Run the **EmployeeChecker.py** 🚀

</div>

<br>


<div align="center">

   ## 🔧 Additional Information

</div>

<div align="left">

For the code to work correctly, follow these steps:
   - Set the path to the default camera

```
   video_capture = cv2.VideoCapture("http://192.168.0.101:8080/video")
```
   *or use your laptop's webcam for testing*

```
   video_capture = cv2.VideoCapture(0)
```

   - in the **employee** folder, upload photos of people whom the system will recognize and write to the database *(or leave the existing photos for the test)*. You should sign the photos by the surnames of your employees
   
📝 Also, for the sake of convenience of using this program, you can add the necessary information to the database for each of the employees, for example: date of birth, phone, email, position, etc.

<br>

</div>