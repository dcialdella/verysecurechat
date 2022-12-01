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

layout = [[sg.Text("VerySecureChat Server")],
          [sg.Input(key='-INPUT-')],
          [sg.Text(size=(40,10), key='-OUTPUT-')],
          [sg.Button('Ok'), sg.Button('Quit')]]

# sg.Window(title="VerySecureChat Server", layout=[[]], margins=(500, 300)).read()
window = sg.Window('VerySecureChat Server', layout)

while True:
    event, values = window.read()
    # See if user wants to quit or window was closed
    if event == sg.WINDOW_CLOSED or event == 'Quit':
        break
    # Output a message to the window
    window['-OUTPUT-'].update('Hello ' + values['-INPUT-'] + "! PySimple ")

window.close()
