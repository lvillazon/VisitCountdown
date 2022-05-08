'''
    VISIT COUNTDOWN CLOCK
    Shows the days remaining until a specified date
    This is designed to run on a Raspberry Pi Zero 2
    with a Hyperpixel touch screen.
    All original code released into the public domain.
    L Villazon 7th May 2022
'''

import sys, pygame, os, time, math
from datetime import timedelta
from enum import Enum


# define values for the finite state machine

class State(Enum):
    RUN = 1
    SET_VISIT = 2
    QUIT = 99


# define the values for the areas of the screen that are counted
# when looking for secret tap codes, to change run state
class Corner(Enum):
    TOP_LEFT = 1
    TOP_RIGHT = 2
    BOTTOM_LEFT = 3
    BOTTOM_RIGHT = 4
    MIDDLE = 0

class Countdown():
    def __init__(self, screen, size):
        self.size = size
        self.screen = screen
        self.next_visit_time = self.get_next_visit_time()
        self.tap_sequence = []  # holds the sequence of corner taps used to switch states
        self.tap_timeout = time.monotonic()
        self.number_font = pygame.font.Font(None, NUMBER_SIZE)
        self.unit_font = pygame.font.Font(None, UNIT_SIZE)
        self.date_font = pygame.font.Font(None, DATE_SIZE)
        self.date_time_font = pygame.font.Font(None, DATE_TIME_SIZE)

    def display_countdown(self):
        # render the days remaining to the screen
        # shows "xx days"
        # unless the time remaining is less than one day, in which case it shows "today"

        # top left of the display text
        # TODO add drift, to prevent screen burn
        xpos = 60 + 60 * math.cos(math.radians((time.monotonic() % 3600) // 10))
        ypos = 130 + 80 * math.sin(math.radians((time.monotonic() % 3600) // 10))

        self.screen.fill(BACKGROUND_COLOR)
        days_to_go = int(self.days_until(self.next_visit_time))
        if days_to_go <1:
            countdown_text = self.number_font.render("today", False, FONT_COLOR)
            self.screen.blit(countdown_text, (xpos, ypos))
        elif days_to_go <2:
            countdown_text = self.number_font.render("1 day", False, FONT_COLOR)
            self.screen.blit(countdown_text, (xpos, ypos))
        else:
            countdown_number = self.number_font.render(str(days_to_go), False, FONT_COLOR)
            countdown_unit = self.unit_font.render(" days", False, FONT_COLOR)
            self.screen.blit(countdown_number, (xpos, ypos))
            self.screen.blit(countdown_unit, (xpos + countdown_number.get_width(), ypos + UNIT_Y_OFFSET))

        # display the actual date/time as well
        current_date_time = self.date_time_font.render(time.strftime('%a %d %b %H:%M'), False, FONT_COLOR)
        self.screen.blit(current_date_time,(xpos, ypos - 20))


        pygame.display.flip()

    def display_visit(self):
        # show the date of the next visit

        # top left of the display text
        xpos = 50
        ypos = 150

        self.screen.fill(BACKGROUND_COLOR)
        visit_text = time.strftime('%a %d %b', self.next_visit_time)
        visit_surf = self.date_font.render(visit_text, False, FONT_COLOR)
        self.screen.blit(visit_surf, (xpos, ypos))
        pygame.display.flip()

    def days_until(self, visit_date):
        # takes a date time object and returns the days until that date
        # this is calculated from midnight at the start of the current date
        # otherwise a visit scheduled for 4pm tomorrow, would show as less than 1 day to go
        # from 16:01 on the day before
        now = time.localtime(time.time())
        day = str(now.tm_mday)
        month = str(now.tm_mon)
        year = str(now.tm_year)
        ref_text = day + ',' + month + ',' + year + ',00,01'
        reference_time = time.strptime(ref_text, '%d,%m,%Y,%H,%M')
        interval = time.mktime(visit_date) - time.mktime(reference_time)
        return interval / (3600 * 24)



    def get_next_visit_time(self):
        # read visit date/time from text file
        with open(CONFIG_FILE, "r") as f:
            next_visit_text = f.readline()

        # return as a datetime object
        return time.strptime(next_visit_text, '%d,%m,%Y,%H,%M')


#    def set_next_visit_time(self, day, month, year, hour, minute):
#        self.next_visit_time =
#        next_visit_list = [str(day), str(month), str(year), str(hour), str(minute)]

    def save_visit_time(self):
        # write visit date/time to text file
        with open(CONFIG_FILE, "w") as f:
            next_visit_text = time.strftime('%d,%m,%Y,%H,%M', self.next_visit_time)
            f.write(next_visit_text)


    def get_corner(self, coords):
        # if coords is sufficiently close to one of the screen corners,
        # return the corner enum, otherwise we return the 'middle' enum
        sensitivity = 0.25
        width = self.size[0]
        height = self.size[1]
        if coords[0] < width*sensitivity and coords[1] <height*sensitivity:
            return Corner.TOP_LEFT
        elif coords[0] < width * sensitivity and coords[1] > height * (1-sensitivity):
            return Corner.BOTTOM_LEFT
        elif coords[0] > width * (1-sensitivity) and coords[1] < height * sensitivity:
            return Corner.TOP_RIGHT
        elif coords[0] > width * (1-sensitivity) and coords[1] > height * (1-sensitivity):
            return Corner.BOTTOM_RIGHT

        else:
            return Corner.MIDDLE

    def check_mouse(self):
        # watches for secret tap codes to see if we should enter
        # one of the other modes, or quit altogether
        # if none is detected, we stay in run mode
        for event in pygame.event.get():
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                #pygame.mouse.set_visible(True)
                mouse_pos = self.get_corner(pygame.mouse.get_pos())
                self.tap_sequence.append(mouse_pos)
                self.tap_timeout = time.monotonic() + 1  # one second
                print(self.tap_sequence)
        if self.tap_sequence == QUIT_CODE:
            return State.QUIT
        elif self.tap_sequence == SET_VISIT_CODE:
            print("set visit")
            self.tap_sequence = []
            return State.SET_VISIT
        elif time.monotonic() > self.tap_timeout:
            self.tap_sequence = []
        else:
            #pygame.mouse.set_visible(False)
            return State.RUN

    def set_visit(self):
        # tap top/bottom of screen to set next visit date
        done = False
        self.tap_timeout = time.monotonic() + 5
        while not done:
            self.display_visit()

            for event in pygame.event.get():
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    mouse_pos = self.get_corner(pygame.mouse.get_pos())
                    self.tap_timeout = time.monotonic() + 5  # one second
                    if mouse_pos == Corner.TOP_RIGHT:
                        self.next_visit_time = time.localtime(time.mktime(self.next_visit_time) - (24*3600))
                    elif mouse_pos == Corner.BOTTOM_RIGHT:
                        self.next_visit_time = time.localtime(time.mktime(self.next_visit_time) + (24*3600))
            if time.monotonic() > self.tap_timeout:
                self.save_visit_time()
                done = True

# setup and initialisation
print("VCC starting up...")

#DEPLOY = "Win"  # switch between windows and pi screen sizes
DEPLOY = "pi"

SIZE = (800, 480)  # use screen resolution for window size
FLAGS = pygame.FULLSCREEN
BACKGROUND_COLOR = (0, 0, 0)
FONT_COLOR = (255, 0, 0)
NUMBER_SIZE = 400
UNIT_SIZE = 200
DATE_SIZE = 150
DATE_TIME_SIZE = 30
UNIT_Y_OFFSET = 120
CONFIG_FILE = "visit_countdown.cfg"
QUIT_CODE = [Corner.TOP_RIGHT, Corner.TOP_RIGHT, Corner.BOTTOM_RIGHT, Corner.BOTTOM_LEFT]
SET_VISIT_CODE = [Corner.TOP_LEFT, Corner.TOP_LEFT, Corner.TOP_LEFT, Corner.BOTTOM_RIGHT]

os.environ["DISPLAY"] = ":0"
pygame.init()
if DEPLOY == "pi":
    screen = pygame.display.set_mode(SIZE, FLAGS)
    #pygame.mouse.set_visible(False)
else:
    screen = pygame.display.set_mode((800,480))
    #pygame.mouse.set_visible(True)
    
pygame.font.init()

# DEBUG test file handling
#set_next_visit_time(9, 5, 2022, 18, 30)
#next_visit = get_next_visit_time()
#print(days_until(next_visit))

countdown = Countdown(screen, SIZE)

# main loop
state = State.RUN
while state is not State.QUIT:
    countdown.display_countdown()

    state = countdown.check_mouse()  # monitor screen tapping
    if state == State.SET_VISIT:
        countdown.set_visit()
        print("finished seting")
        state = State.RUN

pygame.display.quit()
print("VCC finished.")

