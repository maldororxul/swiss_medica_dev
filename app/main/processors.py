from app.amo.processor.processor import SMDataProcessor, CDVDataProcessor

DATA_PROCESSOR = {
    'sm': SMDataProcessor,
    'cdv': CDVDataProcessor,
}
