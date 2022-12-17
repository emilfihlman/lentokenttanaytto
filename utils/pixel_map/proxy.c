//(c) Emil Fihlman

#include <stdint.h>

typedef char s8;
typedef int16_t s16;
typedef int32_t s32;
typedef int64_t s64;
typedef uint8_t u8;
typedef uint16_t u16;
typedef uint32_t u32;
typedef uint64_t u64;

#define F_CPU 16000000UL //16MHz clock

#include <avr/io.h>
//#include <avr/interrupt.h>

#define UART_RX_PIN PIND0
#define UART_TX_PIN PIND1

#define SPI_MOSI_PIN PINB3
#define SPI_MISO_PIN PINB4
#define SPI_SCK_PIN PINB5
#define SPI_SS_PIN PINB2

#define TIMER_FLICKER_PIN PINB1
#define TIMER_LATCH_PIN PIND6

//AVR	Arduino	Function
//PD0	D0	UART RX / Serial
//PD1	D1	UART TX / Serial
//PD6	D6	Data latch
//PB1	D9	LCD refresh
//PB2	D10	Slave select must be output or shenanigans
//PB3	D11	SPI output
//PB4	D12	SPI intput
//PB5	D13	SPI clock

/*
ISR(USART_RX_vect)
{
//...
}
*/

/*
ISR(SPI_STC_vect)
{
//...
}
*/

void gpioSetup(void)
{
	DDRD=_BV(UART_TX_PIN)|_BV(PIND6); //UART TX as output, LATCH as output
	PORTD=_BV(UART_RX_PIN)|_BV(UART_TX_PIN); //UART TX RX pin pullups on
	DDRB=_BV(SPI_MOSI_PIN)|_BV(SPI_SCK_PIN)|_BV(SPI_SS_PIN)|_BV(TIMER_FLICKER_PIN)|_BV(TIMER_LATCH_PIN); //SPI MOSI SCK SS as output, SPI MISO as input, FLICKER LATCH as output
	PORTB=_BV(SPI_MISO_PIN); //Enable pullup on SPI MISO to prevent unnecessary switching
}

void timerSetup(void)
{
	TCCR0A=_BV(WGM01); //CTC mode
	OCR0A=7; //1us to clear from start

	TCCR1A=_BV(COM1A0); //Toggle FLICKER on match
//	OCR1A=62499; //128=F_CPU/(2*N*(1+OCR1A)), F_CPU is 16MHz, N is 1
	OCR1A=15624; //64=F_CPU/(2*N*(1+OCR1A)), F_CPU is 16MHz, N is 8
	TCNT1=0;
//	TCCR1B=_BV(WGM12)|_BV(CS10); //CTC mode, start timer
	TCCR1B=_BV(WGM12)|_BV(CS11); //CTC mode, start timer divived by 8
}

void spiSetup(void)
{
//	SPCR=_BV(SPIE)|_BV(SPE)|_BV(MSTR)|_BV(CPHA)|_BV(SPR1)|_BV(SPR0); //SPI interrupt enable, SPI enable, master mode, leading setup, trailing sample, speed is 16*10^6/128=125kHz
	SPCR=_BV(SPE)|_BV(MSTR)|_BV(CPHA)|_BV(SPR1)|_BV(SPR0); //SPI enable, master mode, leading setup, trailing sample, speed is 16*10^6/128=125kHz
}

u8 spiTransact(u8 data)
{
	SPDR=data;
	loop_until_bit_is_set(SPSR, SPIF);
	return(SPDR);
}

void latchData(void)
{
	loop_until_bit_is_clear(PIND, PIND6);
	PORTD&=~_BV(TIMER_LATCH_PIN); //Stop driving the pin, port control is still active
	TCCR0A&=~_BV(COM0A1); //Disconnect port control
	TCCR0B=0; //Stop time
	PORTD|=_BV(TIMER_LATCH_PIN); //Latch data
	TCCR0A|=_BV(COM0A1); //Reconnect port control, we don't care that this is left running in the background
	TCNT0=0; //Zero timer
	TCCR0B=_BV(CS00); //Start timer
}

void uartSetup(void)
{
	UCSR0A=_BV(U2X0); //Double speed uart
//	UCSR0B=_BV(RXCIE0)|_BV(RXEN0)|_BV(TXEN0); //Enable rx interrupt and rx and tx circuitry
	UCSR0B=_BV(RXEN0)|_BV(TXEN0); //Enable rx and tx circuitry
	UCSR0C=_BV(UCSZ01)|_BV(UCSZ00); //Select 8-bit data
	UBRR0=1; //Select 1MBaud speed
}

void uartWrite(u8 data)
{
	loop_until_bit_is_set(UCSR0A, UDRE0);
	UDR0=data;
}

u8 spiWaitForRepeat(u8 data)
{
	u8 index=0;
	while((++index)!=255 && spiTransact(data)!=data);
	return(index);
}

u8 attemptSizeAutoDetect(void)
{
	u8 repeats[3]={0b01010101, 0b00110011, 0b00001111};
	repeats[0]=spiWaitForRepeat(repeats[0]);
	repeats[1]=spiWaitForRepeat(repeats[1]);
	repeats[2]=spiWaitForRepeat(repeats[2]);
	if(repeats[0]==repeats[1] && repeats[1]==repeats[2])
	{
		return(repeats[0]);
	}
	return(255);
}

s16 main(void)
{
	u8 maxIndex=0, index=0;
	maxIndex=attemptSizeAutoDetect();
	gpioSetup();
	timerSetup();
	spiSetup();
	uartSetup();
//	sei(); //Enable interrupts
//	while(1); //Furiously loooooooop
	while(1)
	{
		u8 uartData;
		loop_until_bit_is_set(UCSR0A, RXC0);
		uartData=UDR0;
		spiTransact(uartData);
		++index;
		if(index==maxIndex)
		{
			index=0;
			uartWrite(255);
			latchData();
		}
	}
	return(0);
}
