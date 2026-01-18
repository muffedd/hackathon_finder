import svgPaths from "./svg-paths";

function Group1() {
  return (
    <div className="absolute contents left-[39.5px] top-[520px]">
      <div className="absolute bg-[#1f1f1f] border-[#2e2e2e] border-[5px] border-solid h-[85px] left-[39.5px] rounded-[32px] top-[520px] w-[481px] shadow-[0px_4px_20px_0px_rgba(0,0,0,0.5)]" />
      <div className="absolute bg-[rgba(217,217,217,0.34)] blur-[7px] filter h-[27px] left-[68.5px] opacity-[0.87] rounded-[10px] top-[530px] w-[411px]" />
      <div className="absolute bg-[rgba(217,217,217,0.66)] blur filter h-[42px] left-[492.5px] opacity-[0.91] rounded-[4px] top-[545px] w-[10px]" />
      <p className="absolute font-['Helvetica:Regular',sans-serif] leading-[normal] left-[186px] not-italic opacity-[0.73] text-[32px] text-nowrap text-white top-[544px] tracking-[-1.28px]">Refer Website</p>
    </div>
  );
}

function Asset() {
  return <div className="absolute h-[63px] left-[106px] top-[77px] w-[74px]" data-name="Asset 2 1" />;
}

function Group() {
  return (
    <div className="absolute inset-[12.89%_82.68%_80.67%_8.21%]" data-name="Group">
      <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 50.9987 41.6114">
        <g id="Group">
          <path d={svgPaths.p27b7ab80} fill="var(--fill-0, #70C496)" id="Vector" />
          <path d={svgPaths.p2769e300} fill="var(--fill-0, #70C496)" id="Vector_2" />
          <path d={svgPaths.pf093000} fill="var(--fill-0, #70C496)" id="Vector_3" />
          <path d={svgPaths.p22681600} fill="var(--fill-0, #70C496)" id="Vector_4" />
          <path d={svgPaths.p90e5000} fill="var(--fill-0, #70C496)" id="Vector_5" />
        </g>
      </svg>
    </div>
  );
}

function Icon() {
  return (
    <div className="absolute contents left-[40px] top-[97px]" data-name="icon">
      <div className="absolute bg-white left-[40px] rounded-[20px] shadow-[0px_4px_11px_1px_rgba(0,0,0,0.21)] size-[64px] top-[72px]" />
      <Group />
    </div>
  );
}

function Layer() {
  return (
    <div className="absolute contents inset-[15.02%_81.43%_75.08%_7.14%]" data-name="Layer 1">
      <Icon />
    </div>
  );
}

function Onlinebutton() {
  return (
    <div className="absolute contents left-[42px] top-[229px]" data-name="onlinebutton">
      <div className="absolute bg-[#d9d9d9] h-[28px] left-[42px] rounded-[10px] top-[229px] w-[82px]" />
      <p className="absolute font-['Arial:Regular',sans-serif] leading-[normal] left-[64px] not-italic text-[14px] text-black text-nowrap top-[235px] tracking-[-0.56px]">Online</p>
    </div>
  );
}

function Group2() {
  return (
    <div className="absolute contents left-[456px] top-[97px]">
      <div className="absolute bg-[#070707] h-[35.556px] left-[456px] rounded-[100px] top-[72px] w-[64px]" />
      <div className="absolute bg-white h-[44.444px] left-[456px] rounded-bl-[18px] rounded-br-[18px] top-[91.56px] w-[64px] shadow-[0px_4px_10px_0px_rgba(0,0,0,0.15)] z-10" />
    </div>
  );
}

function Date() {
  return (
    <div className="absolute contents left-[456px] top-[97px]" data-name="date">
      <Group2 />
      <p className="absolute font-['Helvetica:Regular',sans-serif] leading-[normal] left-[477px] not-italic text-[11px] text-nowrap text-white top-[77px] tracking-[0.22px] z-20">JAN</p>
      <p className="absolute font-['Helvetica:Regular',sans-serif] leading-[normal] left-[475px] not-italic text-[24px] text-black text-nowrap top-[100px] tracking-[-0.96px] z-20">20</p>
    </div>
  );
}

export function HackathonCard() {
  return (
    <div className="bg-white relative rounded-[57px] shadow-[0px_24px_46px_9px_rgba(0,0,0,0.25)] w-[560px] h-[645px] overflow-hidden">
      <Group1 />
      <div className="absolute flex h-[1.992px] items-center justify-center left-[calc(50%+0.5px)] top-[464px] translate-x-[-50%] w-[481px]" style={{ "--transform-inner-width": "0", "--transform-inner-height": "0" } as React.CSSProperties}>
        <div className="flex-none rotate-[0.237deg]">
          <div className="h-0 relative w-[481.004px]">
            <div className="absolute inset-[-3px_0_0_0]">
              <svg className="block size-full" fill="none" preserveAspectRatio="none" viewBox="0 0 481.004 3">
                <line id="Line 1" stroke="var(--stroke-0, #D9D9D9)" strokeWidth="3" x2="481.004" y1="1.5" y2="1.5" />
              </svg>
            </div>
          </div>
        </div>
      </div>
      <Asset />
      <Layer />
      <p className="absolute font-['Helvetica:Regular',sans-serif] leading-[normal] left-[40px] not-italic text-[#575757] text-[32px] text-nowrap top-[402px] tracking-[-1.28px]">Prize : $1K</p>
      <p className="absolute font-['Helvetica:Regular',sans-serif] leading-[normal] left-[428px] not-italic text-[#575757] text-[20px] text-nowrap top-[416px] tracking-[-0.8px]">IIT,Bombay</p>
      <p className="absolute font-['Helvetica:Regular',sans-serif] leading-[normal] left-[42px] not-italic text-[#575757] text-[36px] text-nowrap top-[181px] tracking-[-1.44px]">Hack2Tech Hackathon</p>
      <Onlinebutton />
      <Date />
    </div>
  );
}
