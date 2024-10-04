from fastapi import FastAPI, UploadFile, File
import uvicorn
import zipfile
import os
import fitz  # PyMuPDF
from PIL import Image
import logging
from contextlib import asynccontextmanager
from response import upload_image_as_message

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CURRENT_DIR = os.path.join(os.getcwd(), "uploads")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up the API...")
    yield
    logger.info("Shutting down the API...")

app = FastAPI(
    title="Building App Review System",
    description="An API that helps in reviewing building construction documents.",
    version="1.0.0",
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    lifespan=lifespan
)


def unzip_files(extracted_from, extracted_to):
    os.makedirs(extracted_to, exist_ok=True)
    logging.info("extracting files from a zip.")
    with zipfile.ZipFile(extracted_from, 'r') as file:
        file.extractall(extracted_to)
        


def process_pdf(pdf_path, dpi=300, current_dir: str = CURRENT_DIR):
    """
    Convert each page of the PDF into a high-quality image using PyMuPDF.
    
    Args:
    pdf_path (str): Path to the PDF file
    dpi (int): Dots per inch for image resolution (default: 300)
    
    Returns:
    list: Paths to the extracted images
    """
    folder_path = os.path.join(current_dir, "images")
    os.makedirs(folder_path, exist_ok=True)
    doc = fitz.open(pdf_path)
    image_paths = []
    
    logging.info(len(doc))
    logging.info("converting pdfs to images.")
    
    for i in range(len(doc)):
        page = doc[i]
        
        # Set the matrix for higher resolution
        zoom = dpi / 72  # 72 is the default PDF resolution
        mat = fitz.Matrix(zoom, zoom)
        
        # Get the pixmap using the matrix for higher resolution
        pix = page.get_pixmap(matrix=mat, alpha=False)
        
        # Convert pixmap to PIL Image
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        
        # Save the image with high quality
        # print(folder_path)
        doc_name = doc.name.split("Kindergarten\\")[1].split(".pdf")[0]
        img_path = os.path.join(folder_path, f"{doc_name}_page_{i + 1}.png")
        img.save(img_path, format="PNG", dpi=(dpi, dpi), quality=95)
        
        image_paths.append(img_path)
    
    doc.close()
    return image_paths



@app.get("/")
async def root():
    return {"message": "Welcome to the Fire Protection Review System API"}

@app.post('/upload/')
async def upload_file(file: UploadFile = File(...)):
    try:
        folder_path = os.path.join(os.getcwd(), "uploads")
        file_path:str = os.path.join(folder_path, f"zip")
        #creating folders
        os.makedirs(folder_path,exist_ok=True)
        os.makedirs(file_path, exist_ok=True)
        with open(os.path.join(file_path, file.filename), "wb") as buffer:
            buffer.write(await file.read())
            
        logging.info("unzipping all the files")
        unzip_files(os.path.join(file_path, file.filename), os.path.join(folder_path, "pdfs"))
        logging.info("unzipped done")

        result = [process_pdf(os.path.join(folder_path, "pdfs", "Kindergarten",file)) for file in os.listdir(os.path.join(folder_path, "pdfs", "Kindergarten"))]
        logging.info("converted to images Done")
        
        logging.info("sending images to gpt")
        response = upload_image_as_message(images_path=os.path.join(CURRENT_DIR, "images"))
        logging.info("response:", response)

        return response
        
    except Exception as e:
        return f"Internal server Error: {e}"
        
        
        
        
# Run the FastAPI server
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)