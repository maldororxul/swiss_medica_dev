def run_amo_data_sync(*args):
    from app.main.tasks import SchedulerTask
    SchedulerTask().get_data_from_amo(*args)


def run_pivot_data_builder(*args):
    from app.main.tasks import SchedulerTask
    SchedulerTask().update_pivot_data(*args)
