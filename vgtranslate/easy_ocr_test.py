import easyocr

# Initialize the reader with the desired languages (in this case, Japanese)
reader = easyocr.Reader(['ja'])

# Perform OCR on an image file
results = reader.readtext('prova.png')

# Print out the results
for result in results:
    text = result[1]  # Extract the text from the tuple
    box = result[0]  # Extract the bounding box coordinates from the tuple
    print(f'Text: {text}, Bounding Box: {box}')
