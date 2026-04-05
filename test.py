import smtplib

server = smtplib.SMTP("smtp.gmail.com", 587)
server.starttls()
server.login("madhuramirajakar61@gmail.com", "hlkaodhcbgvhwneg")
print("LOGIN SUCCESS")