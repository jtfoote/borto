# from serial_reader import read_and_store_metrics
# from serial_lcd import write_to_lcd
from shared.models import engine, init_db, SystemMetric
from stm_comm import STM32Comm, STMStringException
from sqlalchemy.orm import Session

def main():
    init_db()
    stm32 = STM32Comm()
    if stm32.sim:
        print("WARNING: Hardware not found, entering simulation mode.", flush=True)
    tick = 0
    while True:
        with Session(engine) as db:
            if stm32.sim:
                tick += 1
                try:
                    message = stm32.gen_message(tick % 6)
                except STMStringException as e:
                    print(e, flush=True)
                    continue
            else:
                try:
                    message = stm32.read_message()
                except Exception as e:
                    print(e, flush=True)
            # print(message, flush=True)
            db_entry, status = stm32.parse_message(message)
            db.add(db_entry)
            db.commit()

if __name__ == '__main__':
    main()