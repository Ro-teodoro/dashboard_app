
FROM python:3.10-slim-bullseye

ENV APP_HOME /app
ENV PYTHONUNBUFFERED True
WORKDIR $APP_HOME

ADD . .
ENV HOST 34.66.66.156
ENV DATABASE dashboards
ENV USER postgres
ENV PASSWORD KurT262246

ENV esqu Dashboards
ENV estad suma,promedio,conteo
ENV temas Poblacion,Economia
ENV bds caracteristicas_poblacionales,caracteristicas_economicas
ENV agreg colonias,delegaciones,sectores,subsectores

RUN apt-get update
RUN apt-get install nano

RUN pip install --no-cache-dir -r requirements.txt && pip install --no-cache-dir gunicorn
RUN pip install psycopg2-binary

RUN groupadd -r app && useradd -r -g app app
COPY --chown=app:app . ./
USER app

EXPOSE 8080

CMD ["python","-u","./app.py"]
