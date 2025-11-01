def leer_info_supermercado():
	with open("../prompts_finales/info_supermercado.txt", "r", encoding="utf-8") as f:
		contenido = f.read().strip()
	return contenido
