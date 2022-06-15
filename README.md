# Docket Digitiser - Building an OCR Solution with Azure's Form Recognizer
This is the code we used when building our OCR solution to extract the important information from Delivery Dockets. 
The solution works by:

1. Connect to you Blob Storage containers. Here we have three:
    * The Raw container holds the dockets that need to be processed.
    * The Processed container holds the original dockets that have been processed.
    * The Results container holds `.xlsx` files of the the extracted text.
2. Next we get the urls for the blobs in the Raw container.
3. The urls are then passed to Azure's Form Recognizer to parse the relavent fields from the forms.
4. The extracted text is then processed saved as a `.xlsx` file.
5. Conditional formating is applied to the `.xlsx` file to highlight the confidence values of the OCR algorithm.
6. The `.xlsx` is then saved as blobs in the Results container. 
7. The original docket is saved as a blob in the Processed container and removed from the Raw container. 

## BlobTrigger - Python

The `BlobTrigger` makes it incredibly easy to react to new Blobs inside of Azure Blob Storage. This sample demonstrates a simple use case of processing data from a given Blob using Python.

## How it works

For a `BlobTrigger` to work, you provide a path which dictates where the blobs are located inside your container, and can also help restrict the types of blobs you wish to return. For instance, you can set the path to `samples/{name}.png` to restrict the trigger to only the samples path and only blobs with ".png" at the end of their name.
