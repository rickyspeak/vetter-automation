from icalendartools import IcalendarTools
from vetterTools import VetterTools


def main():
    vetter = VetterTools()
    vetter.getCreds()
    appointments = vetter.getAppointments(3)

    ical = IcalendarTools()
    ical.getCreds()
    ical.postAppointments(appointments)


if __name__ == '__main__':
    main()
