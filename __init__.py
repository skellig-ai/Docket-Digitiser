import logging
import azure.functions as func
from azure.storage.blob import BlobServiceClient
import pandas as pd
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
import io


def main(myblob: func.InputStream):
    logging.info(f'Python blob trigger function processed blob: {myblob.name}')

    credentials = Credentials()
    blob_service_client = BlobServiceClient.from_connection_string(credentials.storage_connect_str)

    raw_container_client = blob_service_client.get_container_client('raw')
    logging.info('Connected to RAW storage container.')
    processed_container_client = blob_service_client.get_container_client('processed')
    logging.info('Connected to PROCESSED storage container.')
    result_container_client = blob_service_client.get_container_client('results')
    
    formUrlBase = raw_container_client.primary_endpoint

    blob_list = raw_container_client.list_blobs()
    for blob in blob_list:
        docket_url = f'{formUrlBase}/{blob.name}'
        logging.info(f'Parsing text from docket at URL: {docket_url}')
        df = docket_parser(credentials, docket_url)
        create_xlsx(df, processed_container_client, blob.name)

        logging.info(f'Saving parsed text from {blob.name} into Results blob container')
        processed_container_client.upload_blob(blob, blob.blob_type, overwrite=True)
        raw_container_client.delete_blob(blob)

    return func.HttpResponse(
             'This Blob triggered function executed successfully.',
             status_code=200
        )


class Credentials:
    storage_connect_str = 'connection_string'
    model_endpoint = 'model_endpoint'
    model_key = 'model_key'
    model_id = 'model_id'

def docket_parser(credentials, docket):
    document_analysis_client = DocumentAnalysisClient(endpoint=credentials.model_endpoint, credential=AzureKeyCredential(credentials.model_key))
    logging.info(f'Docket URL: {docket}')
    logging.info(f'Model ID: {credentials.model_id}')
    poller = document_analysis_client.begin_analyze_document_from_url(credentials.model_id, docket)
    result = poller.result()
    document = result.documents[0]
    
    df = results_df(document)
    name = df['Text Entered'][1]

    logging.info(f'Exporter name: {name}')
    return df

def results_df(document):
  fields, text, confidence = get_columns(document)
  data = {'Field': fields,
          'Text Entered': text, 
          'Confidence' : confidence}
  return pd.DataFrame(data, index=None)

def get_columns(document):
  fields = list(document.fields.keys())
  text = []
  confidence = []
  for field_value in document.fields.values():
    text.append(field_value.value)
    confidence.append(field_value.confidence)
  return fields, text, confidence

def create_xlsx(df, processed_container_client, blob_name):
    fname = f'{blob_name[0:-4]}_results.xlsx'
    result_blob = processed_container_client.get_blob_client(fname)
    logging.info(f'Created result_blob for docket {blob_name}')

    xlb=io.BytesIO()
    writer = pd.ExcelWriter(xlb, engine= 'xlsxwriter')

    # Convert the dataframe to an XlsxWriter Excel object.
    df.to_excel(writer, sheet_name='Sheet1')

    # Get the xlsxwriter workbook and worksheet objects.
    workbook  = writer.book
    worksheet = writer.sheets['Sheet1']


    # Add a format. Light red fill with dark red text.
    red_format = workbook.add_format({'bg_color': '#FFC7CE', 'font_color': '#9C0006'})
    yellow_format = workbook.add_format({'bg_color': '#FFEB9C', 'font_color': '#9C5700'})
    green_format = workbook.add_format({'bg_color': '#C6EFCE', 'font_color': '#006100'})

    # Set the conditional format range.
    start_row = 1
    start_col = 3
    end_row = len(df)
    end_cold = start_col

    # Apply a conditional format to the cell range.
    worksheet.conditional_format(start_row, start_col, end_row, end_cold,
                                {'type':    'cell',
                                'criteria': 'less than or equal to',
                                'value':    0.8,
                                'format':   red_format})
    worksheet.conditional_format(start_row, start_col, end_row, end_cold,
                                {'type':     'cell',
                                'criteria': 'between',
                                'maximum':  0.9,
                                'minimum':  0.8,
                                'format':   yellow_format})
    worksheet.conditional_format(start_row, start_col, end_row, end_cold,    
                                {'type':    'cell',
                                'criteria': 'greater than or equal to',
                                'value':    0.9,
                                'format':   green_format})

    writer.save()
    xlb.seek(0)
    result_blob.upload_blob(xlb, overwrite=True)
