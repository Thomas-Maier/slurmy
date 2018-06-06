
from slurmy import JobHandler
from slurmy import SingularityWrapper


def main():
    ## The singularity image that should be used
    image = 'my_singularity_image.img'
    ## The "insitu" option defines if the wrapping is applied in the run_script itself (True) or via an additional dummy script (False)
    ## Setting insitu to False may be necessary if you can't access the run_script from within itself
    singularityWrapper = SingularityWrapper(image, insitu = True)
    ## Pass wrapper to jobhandler instance
    jobHandler = JobHandler(wrapper = singularityWrapper)

    run_script = """
    echo "where am I?"
    cat /etc/issue
    """

    jobHandler.add_job(run_script = run_script)

    jobHandler.run_jobs(interval = 2)

if __name__ == '__main__':
    main()
