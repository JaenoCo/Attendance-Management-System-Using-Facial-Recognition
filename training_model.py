from sklearn.preprocessing import LabelEncoder
from sklearn.svm import SVC
import argparse
import pickle
import os

ap = argparse.ArgumentParser()
ap.add_argument('-e', '--embeddings', 
                default='output/embeddings.pickle',
                help='path to serialized database of facial embeddings (default: output/embeddings.pickle)')
ap.add_argument('-r','--recognizer',
                default='output/recognizer.pickle',
                help='path to output model trained to recognize faces (default: output/recognizer.pickle)')
ap.add_argument('-l','--le',
                default='output/le.pickle',
                help='path to output label encoder (default: output/le.pickle)')

args = vars(ap.parse_args())

# Check if embeddings file exists
if not os.path.exists(args['embeddings']):
    print(f"[ERROR] Embeddings file not found: {args['embeddings']}")
    print("[ERROR] Please run extract_embeddings.py first to generate embeddings from your dataset")
    print("[INFO] Usage: python extract_embeddings.py")
    exit(1)

print('[INFO] Loading face embeddings...')
data = pickle.loads(open(args['embeddings'], 'rb').read())

if len(data['names']) == 0:
    print("[ERROR] No embeddings found in the serialized data")
    exit(1)

print(f'[INFO] Found {len(data["names"])} face embeddings')
print(f'[INFO] Students: {set(data["names"])}')

print('[INFO] Encoding labels...')
le = LabelEncoder()
labels = le.fit_transform(data['names'])

print('[INFO] Training SVM model...')
recognizer = SVC(C=1.0, kernel='linear', probability=True)
recognizer.fit(data['embeddings'],labels)

# Create output directory if it doesn't exist
os.makedirs(os.path.dirname(args['recognizer']) or '.', exist_ok=True)

print(f'[INFO] Saving recognizer to {args["recognizer"]}...')
f = open(args['recognizer'],'wb')
f.write(pickle.dumps(recognizer))
f.close()

print(f'[INFO] Saving label encoder to {args["le"]}...')
f = open(args['le'],'wb')
f.write(pickle.dumps(le))
f.close()

print('[SUCCESS] Training complete!')
print(f'[INFO] Recognizer saved: {args["recognizer"]}')
print(f'[INFO] Label encoder saved: {args["le"]}')