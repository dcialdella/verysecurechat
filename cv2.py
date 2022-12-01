#! python3

# https://realpython.com/pysimplegui-python/
# https://github.com/vinta/awesome-python

#
# Testing Python Code v3
# python --version      Python 2.7.5
# python3 --version     Python 3.6.8

import random, sys, os, math, copy, pprint, pyautogui
import PySimpleGUI as sg

sg.theme('light green 2')

# pyautogui.alert('Alert Box.')
# pyautogui.confirm('Continuamos?')

gpgid=pyautogui.prompt('Indicar GPG ID?')

sg.Window(title="VerySecureChat Client", layout=[[]], margins=(500, 300)).read()

# wh = pyautogui.size() # Obtain the screen resolution.
# wh                    # Size(width=1920, height=1080)

# pyautogui.moveTo(100, 100, duration=0.25)
# pyautogui.position() # Get current mouse position again.
# pyautogui.click(10, 5) # Move mouse to (10, 5) and click.
# pyautogui.drag(distance, 0, duration=0.2)
# pyautogui.click()
# pyautogui.scroll(200)
# im = pyautogui.screenshot()

