from __future__ import print_function
import click
import re
import face_recognition.api as face_recognition
import multiprocessing
import itertools
import sys
import PIL.Image
import numpy as np
print("Welcome to  photo analyzer , wait for script working..........");
import requests
import random
import string
import urllib.request
import os
import face_recognition
import uuid
import psycopg2
import subprocess
import shlex


res_type = ''

# #	# #	#Начало объявления бибилиотек распознавания

def scan_known_people(known_people_folder):
  known_names = []
  known_face_encodings = []

  for file in image_files_in_folder(known_people_folder):
    basename = os.path.splitext(os.path.basename(file))[0]
    img = face_recognition.load_image_file(file)
    encodings = face_recognition.face_encodings(img)

    if len(encodings) > 1:
      click.echo("WARNING: More than one face found in {}. Only considering the first face.".format(file))

    if len(encodings) == 0:
      click.echo("WARNING: No faces found in {}. Ignoring file.".format(file))
    else:
      known_names.append(basename)
      known_face_encodings.append(encodings[0])

  return known_names, known_face_encodings


def print_result(filename, name, distance, show_distance = False):
	print("{},{}".format(filename, name))
	return name


def test_image(image_to_check, known_names, known_face_encodings, tolerance = 0.6, show_distance = False, name_result = ''):
    unknown_image = face_recognition.load_image_file(image_to_check)

    # Scale down image if it's giant so things run a little faster
    if max(unknown_image.shape) > 1600:
      pil_img = PIL.Image.fromarray(unknown_image)
      pil_img.thumbnail((1600, 1600), PIL.Image.LANCZOS)
      unknown_image = np.array(pil_img)

    unknown_encodings = face_recognition.face_encodings(unknown_image)

    for unknown_encoding in unknown_encodings:
      distances = face_recognition.face_distance(known_face_encodings, unknown_encoding)
      result = list(distances <= tolerance)

      if True in result:
        name_result = [print_result(image_to_check, name, distance, False) for is_match, name, distance in zip(result, known_names, distances) if is_match]
        return name_result
      else:
        name_result = print_result(image_to_check, "unknown_person", None, False)
        return name_result

    if not unknown_encodings:
      # print out fact that no faces were found in image
      print_result(image_to_check, "no_persons_found", None, False)
      name_result = "no_persons_found"
      return name_result


def image_files_in_folder(folder):
    return [os.path.join(folder, f) for f in os.listdir(folder) if re.match(r'.*\.(jpg|jpeg|png)', f, flags=re.I)]


def process_images_in_process_pool(images_to_check, known_names, known_face_encodings, number_of_cpus, tolerance, show_distance, name_result):
    if number_of_cpus == -1:
      processes = None
    else:
      processes = number_of_cpus

    # macOS will crash due to a bug in libdispatch if you don't use 'forkserver'
    context = multiprocessing
    if "forkserver" in multiprocessing.get_all_start_methods():
      context = multiprocessing.get_context("forkserver")

    pool = context.Pool(processes=processes)

    function_parameters = zip(
      images_to_check,
      itertools.repeat(known_names),
      itertools.repeat(known_face_encodings),
      itertools.repeat(tolerance),
      itertools.repeat(False)
    )

    pool.starmap(test_image, function_parameters)


# @click.command()
# @click.argument('known_people_folder')
# @click.argument('image_to_check')
# @click.option('--cpus', default=1, help='number of CPU cores to use in parallel (can speed up processing lots of images). -1 means "use all in system"')
# @click.option('--tolerance', default=0.6, help='Tolerance for face comparisons. Default is 0.6. Lower this if you get multiple matches for the same person.')
# @click.option('--show-distance', default=False, type=bool, help='Output face distance. Useful for tweaking tolerance setting.')
def face_reco(known_people_folder, image_to_check, cpus, tolerance, show_distance):
    known_names, known_face_encodings = scan_known_people(known_people_folder)

    # Multi-core processing only supported on Python 3.4 or greater
    if (sys.version_info < (3, 4)) and cpus != 1:
      click.echo("WARNING: Multi-processing support requires Python 3.4 or greater. Falling back to single-threaded processing!")
      cpus = 1

    if os.path.isdir(image_to_check):
      if cpus == 1:
      	[test_image(image_file, known_names, known_face_encodings, tolerance, False, name) for image_file in image_files_in_folder(image_to_check)]
      else:
      	process_images_in_process_pool(image_files_in_folder(image_to_check), known_names, known_face_encodings, cpus, tolerance, False)
    else:
      name = test_image(image_to_check, known_names, known_face_encodings, tolerance, False)
      return name

# #	# #	#Конец объявления бибилиотек распознавания




if __name__ == "__main__":
	name_result = ''
	con = psycopg2.connect(dbname = 'check', user = 'postgres', password = 'user', host = "127.0.0.1",port = "5432")
	print("Database opened successfully")
	cur = con.cursor()

	cur.execute('''CREATE TABLE IF NOT EXISTS IMAGE_IDENTIFY (URL TEXT NOT NULL,NAME TEXT NOT NULL);''')
	con.commit()
	print('Table connected\n')

	while 1:
		
		print('Please, enter URL of a picture to identify(or you can enter \'end\' if you want and this session; or \'show\' if you want see base):')

		url = input()
		if(url == "end"):
			print('Goodbuy')
			cur.close()
			con.close()
			sys.exit()

		if(url == "show"):
			cur.execute("SELECT url, name from IMAGE_IDENTIFY")
			rows = cur.fetchall()
			print(rows)
			for row in rows:  
			  print("url = ", row[0])
			  print("uuid = ", row[1])
			print()
			continue
#or (url[0:6] != "http://")
		if(url[0:4] != "http"):
			print('Wrong url\n')
			continue

		img = urllib.request.urlopen(url).read()
		name = "img"
		out = open(name + ".jpg", "wb")
		out.write(img)
		out.close()

		name_result = face_reco("C:\LABS\sface_task\People", "img.jpg", -1, 0.6, False)
		
		if(name_result == "no_persons_found"):
			print('There is no faces on image')

		elif(name_result == "unknown_person"):
			print('There is unknown_person\nPlease, enter the Name you would like to assign to this image')
			name_result = input()
			os.remove("img.jpg")
			name_result = "People\\" + name_result
			print("Image is saved as ",name_result[7::],'.jpg')
			cur.execute("INSERT INTO IMAGE_IDENTIFY (URL,NAME) VALUES ('%s','%s');""" %(url, name_result[7::]))
			name_result = name_result + ".jpg" 
			out = open(name_result, "wb")
			out.write(img)
			out.close()

		else:
			print('Is that', name_result[0], 'on image?')
			answer = input()
			if(answer == "Yes") or (answer == "yes") or (answer == "y"):
				print('Good')
				cur.execute("INSERT INTO IMAGE_IDENTIFY (URL,NAME) VALUES ('%s','%s');""" %(url, name_result[0]))
			elif(answer == "No") or (answer == "no") or (answer == "n"):
				print('Sorry')
				cur.execute("INSERT INTO IMAGE_IDENTIFY (URL,NAME) VALUES ('%s','%s');""" %(url, name_result[7::]))
			else:
				print('I can\'t understand you')

		con.commit()

"""
Usage: face_recognition [OPTIONS] KNOWN_PEOPLE_FOLDER IMAGE_TO_CHECK

Options:
  --cpus INTEGER           number of CPU cores to use in parallel (can speed
                           up processing lots of images). -1 means "use all in
                           system"
  --tolerance FLOAT        Tolerance for face comparisons. Default is 0.6.
                           Lower this if you get multiple matches for the same
                           person.
  --show-distance BOOLEAN  Output face distance. Useful for tweaking tolerance
                           setting.
"""