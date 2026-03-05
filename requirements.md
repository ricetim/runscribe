THIS FILE CONTAINS A RUNNING LOG OF PROJECT REQUIREMENTS, ORGANIZED BY DATE OF ADDITION.

# 2023-03-04
project will be a running fitness dashboard, showcasing workouts and analysis of the
import .fit files from coros pace 4
	can it come directly from coros, or does it need to come from strava? does coros have an api?
	if data cannot come from coros, determine if it can come from strava via their api, or even from runalyze.
	can it import the training notes from coros that I make after every workout?
display a log of previous runs, with personal notes and stats
compute running statistics similar to what runalyze does
	old runalyze git repo can be found here: https://github.com/runalyze
	current runalyze docs here: https://runalyze.com/
allow for precision analysis of small portions of the workout. Don't compress data!
import and showcase photos from the run (likely from strava) if they exist
track gear usage (shoes)
show an interactive map of the run
allow for goal setting (mileage totals, etc) and tracking of those goals
this should run as a docker container
photos with gps data should be shown on the map for a workout 
should include the creation of training plans for popular sources like daniels and pfitzinger
research how running metrics are calculated from first principles
	metrics of interest: VO2Max, race time predictions (5k/10k/half/marathon), training stress, lactate threshold, running economy
	source research papers where possible; note any book sources so they can be procured
Add ability to create workouts based on the Daniels white, red, blue, and gold training plans detailed in his running formula book
review this webpage for information:  https://fellrnr.com/wiki/Modeling_Human_Performance#The_Banister_Formula
