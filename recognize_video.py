from imutils.video import VideoStream
from imutils.video import FPS
import numpy as np
import argparse
import cv2
import imutils
import pickle
import time
import os
import sys

ap = argparse.ArgumentParser()
ap.add_argument('-d','--detector', default='Models',
                help='path to face detector (default: Models)')
ap.add_argument('-m','--embedding-model', default='openface_nn4.small2.v1.t7',
                help='path to face embedding model (default: openface_nn4.small2.v1.t7)')
ap.add_argument('-r','--recognizer', default='output/recognizer.pickle',
                help='path to model trained to recognize faces (default: output/recognizer.pickle)')
ap.add_argument('-l','--le', default='output/le.pickle',
                help='path to label encoder (default: output/le.pickle)')
ap.add_argument('-c','--confidence', type=float, default=0.5,
                help='minimum probability of face detection (default: 0.5)')

args = vars(ap.parse_args())

# Validate required files exist
required_files = [
    (args['detector'], 'deploy.prototxt'),
    (args['detector'], 'res10_300x300_ssd_iter_140000.caffemodel'),
    (args['embedding_model'], None),
    (args['recognizer'], None),
    (args['le'], None)
]

print('[INFO] Loading face detector...')
protoPath = os.path.sep.join([args['detector'],'deploy.prototxt'])
modelPath = os.path.sep.join([args['detector'],'res10_300x300_ssd_iter_140000.caffemodel'])

if not os.path.exists(protoPath) or not os.path.exists(modelPath):
    print(f"[ERROR] Face detector not found at {args['detector']}")
    sys.exit(1)

detector = cv2.dnn.readNetFromCaffe(protoPath, modelPath)

print('[INFO] Loading face embedder...')
if not os.path.exists(args['embedding_model']):
    print(f"[ERROR] Face embedding model not found: {args['embedding_model']}")
    sys.exit(1)

embedder = cv2.dnn.readNetFromTorch(args['embedding_model'])

print('[INFO] Loading recognizer and label encoder...')
if not os.path.exists(args['recognizer']) or not os.path.exists(args['le']):
    print(f"[ERROR] Recognizer models not found")
    print(f"[ERROR] Make sure to train the model first:")
    print("[ERROR]   1. python extract_embeddings.py")
    print("[ERROR]   2. python training_model.py")
    sys.exit(1)

recognizer = pickle.loads(open(args['recognizer'], 'rb').read())
le = pickle.loads(open(args['le'], 'rb').read())

print('[INFO] Starting video stream...')
print('[INFO] Press Q to quit')

vs = VideoStream(src=0).start()
time.sleep(2.0)

fps = FPS().start()

while True:
	frame = vs.read()
	frame = imutils.resize(frame, width=600)
	(h, w) = frame.shape[:2]
	imageBlob = cv2.dnn.blobFromImage(cv2.resize(frame,(300,300)), 1.0, (300,300), (104.0,177.0,123.0), swapRB=False, crop=False)

	detector.setInput(imageBlob)
	detections = detector.forward()

	for i in range(0, detections.shape[2]):
		confidence = detections[0,0,i,2]

		if confidence > args['confidence']:
			box = detections[0,0,i,3:7] * np.array([w,h,w,h])
			(startX, startY, endX, endY) = box.astype('int')

			face = frame[startY:endY, startX:endX]

			(fH, fW) = face.shape[:2]

			if fW < 20 or fH < 20:
				continue

			faceBlob = cv2.dnn.blobFromImage(face, 1.0/255, (96,96), (0,0,0), swapRB=True, crop=False)
			embedder.setInput(faceBlob)
			vec = embedder.forward()

			pred = recognizer.predict_proba(vec)[0]

			j = np.argmax(pred)
			proba = pred[j]
			name = le.classes_[j]

			text = '{}: {:.2f}%'.format(name, proba * 100)

			y = startY - 10 if startY - 10 > 10 else startY + 10
			cv2.rectangle(frame, (startX, startY), (endX, endY), (0, 255, 0), 2)
			cv2.putText(frame, text, (startX, y), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 2)

	fps.update()

	cv2.imshow('Face Recognition', frame)
	if cv2.waitKey(1) & 0xFF == ord('q'):
		break

fps.stop()
print('[INFO] Time elapsed: {:.2f}s'.format(fps.elapsed()))
print('[INFO] FPS: {:.2f}'.format(fps.fps()))

cv2.destroyAllWindows()
vs.stop()
print('[INFO] Video stream closed')