# ReposterBot

Итак в чем идея:
- пользователь запустил бота
- бот его поприветствовал, предлагает клавиатуру
- дальше разные сценарии:
- (1)
  - пользователь нажимает "Add link" 
  - в потоке выполнения ожидается список ссылок
  - после получения ссылок бот сохраняет их в файле устанавливая стандартные настройки
- (2)
  - пользователь нажимает "Settings"
  - в потоке выполнения ожидается изменение настроек
  - после получения настроек бот сохраняет их в файле
- (3)
  - пользователь нажимает "Del link"
  - в потоке выполнения ожидается список на удаление (если удалять нечего или неоткуда, то выход из потока)
  - после получения списка бот обновляет файл
- после задания всех настроек и передачи ссылок, бот спустя установленное время собирает со всех ссылок 
инфу о публикациях и репостит их пользователю.