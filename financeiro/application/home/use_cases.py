from datetime import datetime


class HomeUseCases:
    def __init__(self, repository):
        self.repository = repository

    def listar_anos(self, ano_atual=None):
        anos = self.repository.get_anos()
        if not anos:
            anos.add(datetime.now().year)
        if ano_atual:
            anos.add(ano_atual)
        return sorted(anos, reverse=True)

