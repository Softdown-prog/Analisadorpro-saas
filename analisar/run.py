# run.py
import click
from flask.cli import FlaskGroup
from app import create_app

app = create_app()

@click.group(cls=FlaskGroup, create_app=create_app)
def cli():
    """Gerenciamento de comandos para a aplicação Analisador PRO."""
    pass

# Se você quiser que o Flask CLI use 'run.py' como seu ponto de entrada padrão:
# Remova a linha if __name__ == '__main__': app.run(debug=True)
# E o comando para iniciar o servidor seria 'flask run'

if __name__ == '__main__':
    # Quando você executa 'python run.py', ele ainda vai rodar o servidor web.
    # Mas se você usar 'flask', ele vai usar a função cli.
    app.run(debug=True)