from googleCalTools import GoogleCalTools
from vetterTools import VetterTools

def main():
    vetter = VetterTools()
    vetter.login()
    appointments = vetter.getAppointments(3)

    ical = GoogleCalTools()
    ical.getCreds()
    ical.postAppointments(appointments)


if __name__ == '__main__':
    main()
