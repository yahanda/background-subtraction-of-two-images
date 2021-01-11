import os
import io
import time
import numpy as np
import cv2
from urllib.request import urlopen
from flask import Flask, render_template, request, redirect, url_for
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from dotenv import load_dotenv
from azure.storage.blob import BlobServiceClient
from azure.storage.blob import generate_container_sas, ContainerSasPermissions
from azure.storage.blob import generate_blob_sas, BlobSasPermissions

load_dotenv()
account_name = os.environ.get("ACCOUNT_NAME")
account_key = os.environ.get("ACCOUNT_KEY")
connect_str = os.environ.get("CONNECT_STR")
container_name = os.environ.get("CONTAINER_NAME")

blob_service_client = BlobServiceClient.from_connection_string(connect_str)
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'PNG', 'JPG'])
IMAGE_WIDTH = 640

# using generate_container_sas
def get_img_url_with_container_sas_token(blob_name):
    container_sas_token = generate_container_sas(
        account_name=account_name,
        container_name=container_name,
        account_key=account_key,
        permission=ContainerSasPermissions(read=True),
        expiry=datetime.utcnow() + timedelta(hours=1)
    )
    blob_url_with_container_sas_token = f"https://{account_name}.blob.core.windows.net/{container_name}/{blob_name}?{container_sas_token}"
    return blob_url_with_container_sas_token

# using generate_blob_sas
def get_img_url_with_blob_sas_token(blob_name):
    blob_sas_token = generate_blob_sas(
        account_name=account_name,
        container_name=container_name,
        blob_name=blob_name,
        account_key=account_key,
        permission=ContainerSasPermissions(read=True),
        expiry=datetime.utcnow() + timedelta(hours=1)
    )
    blob_url_with_blob_sas_token = f"https://{account_name}.blob.core.windows.net/{container_name}/{blob_name}?{blob_sas_token}"
    return blob_url_with_blob_sas_token

def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/send', methods=['GET', 'POST'])
def send():
    if request.method == 'POST':
        source_file = request.files['source_file']
        target_file = request.files['target_file']

        # check the extension
        if source_file and allowed_file(source_file.filename):
            source_filename = secure_filename(source_file.filename)
        else:
            return ' <p>許可されていない拡張子です</p> '
        if target_file and allowed_file(target_file.filename):
            target_filename = secure_filename(target_file.filename)
        else:
            return ' <p>許可されていない拡張子です</p> '

        # upload to blob
        source_blob_client = blob_service_client.get_blob_client(container=container_name, blob=source_filename)
        source_blob_client.upload_blob(source_file, overwrite=True)
        source_img_url = get_img_url_with_blob_sas_token(source_filename)
        target_blob_client = blob_service_client.get_blob_client(container=container_name, blob=target_filename)
        target_blob_client.upload_blob(target_file, overwrite=True)
        target_img_url = get_img_url_with_blob_sas_token(target_filename)

        # read images
        source_req = urlopen(source_img_url)
        source_arr = np.asarray(bytearray(source_req.read()), dtype=np.uint8)
        source_img = cv2.imdecode(source_arr, -1) # 'Load it as it is'
        target_req = urlopen(target_img_url)
        target_arr = np.asarray(bytearray(target_req.read()), dtype=np.uint8)
        target_img = cv2.imdecode(target_arr, -1) # 'Load it as it is'

        # change size
        #source_img = cv2.resize(img1, (IMAGE_WIDTH, int(IMAGE_WIDTH*img1.shape[0]/img1.shape[1])))
        #target_img = cv2.resize(img2, (IMAGE_WIDTH, int(IMAGE_WIDTH*img2.shape[0]/img2.shape[1])))

        # diff images
        fgbg = cv2.bgsegm.createBackgroundSubtractorMOG()
        fgmask = fgbg.apply(source_img)
        fgmask = fgbg.apply(target_img)
        diff_img = cv2.imencode('.jpg', fgmask)[1].tostring()
        diff_filename = "DIFF_" + source_filename + "_" + target_filename

        # upload to blob
        diff_blob_client = blob_service_client.get_blob_client(container=container_name, blob=diff_filename)
        diff_blob_client.upload_blob(diff_img, overwrite=True)
        diff_img_url = get_img_url_with_blob_sas_token(diff_filename)

        return render_template('index.html', source_img_url=source_img_url, target_img_url=target_img_url, diff_img_url=diff_img_url)

    else:
        return redirect(url_for('index'))

if __name__ == '__main__':
    app.debug = True
    app.run(host='0.0.0.0')