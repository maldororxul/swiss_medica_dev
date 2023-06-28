from app.amo.sync.controller import SMSyncController, CDVSyncController

SYNC_CONTROLLER = {
    'sm': SMSyncController,
    'cdv': CDVSyncController,
}
