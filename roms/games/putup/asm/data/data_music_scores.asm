; Данные: data_music_scores
; Адрес: 0x3E1A
; Размер: 15 байт
; Описание: Заголовки музыкальных дорожек (score-header table): указатели/параметры треков, читаются func_music_load_score.
data_music_scores:
    DEFB 038h, 06h, 06h, 0Fh, 00h, 0Eh, 060h, 060h
    DEFB 060h, 01Fh, 00h, 03h, 02h, 05h, 00h
