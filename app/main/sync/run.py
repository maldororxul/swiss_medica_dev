def run(*args):
    from app.main.tasks import SchedulerTask
    SchedulerTask().get_data_from_amo(*args)
