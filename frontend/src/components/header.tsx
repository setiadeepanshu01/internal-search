import mm from 'images/mm.png'
import morgan from 'images/morgan.png' 

export const Header = () => (
  <div className="flex flex-row justify-between items-center space-x-6 px-8 py-3.5 bg-black w-full">
    <div className="pr-8 border-r border-ink">
      <a href="/">
        <img width={118} height={30} src={mm} alt="Logo" />
      </a>
    </div>
    <div className="flex-grow flex justify-center">
      <img width={236} height={30} src={morgan} alt="Logo" className="max-w-full" />
    </div>
    <div className="w-[118px]"></div>
  </div>
)