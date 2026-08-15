import { FormEvent, useState } from "react";
import image from "./image.svg";
import line1 from "./line-1.svg";
import line2 from "./line-2.svg";
import vector from "./vector.svg";
import vector2 from "./vector-2.svg";
import vector3 from "./vector-3.svg";
import vector4 from "./vector-4.svg";
import vector5 from "./vector-5.svg";
import vector6 from "./vector-6.svg";
import vector7 from "./vector-7.svg";
import vector8 from "./vector-8.svg";
import vector9 from "./vector-9.svg";
import vector10 from "./vector-10.svg";
import vector11 from "./vector-11.svg";
import vector12 from "./vector-12.svg";
import vector158Stroke from "./vector-158-stroke.svg";
import vectorStroke from "./vector-stroke.svg";
import vectorStroke2 from "./vector-stroke-2.svg";

const dates = [
  { day: "29", weekday: "MON", muted: true },
  { day: "30", weekday: "TUE", muted: true },
  { day: "1", weekday: "WED", muted: false },
  { day: "2", weekday: "THU", muted: false },
  { day: "3", weekday: "FRI", muted: true },
  { day: "4", weekday: "SAT", muted: true },
];

const timeSlots = [
  { label: "9:00 AM", state: "available" },
  { label: "9:30 AM", state: "available" },
  { label: "10:00 AM", state: "selected" },
  { label: "19:30 AM", state: "available" },
  { label: "11:00 AM", state: "available" },
  { label: "11:30 AM", state: "busy" },
  { label: "12:00 M", state: "available" },
  { label: "12:30 M", state: "available" },
  { label: "1:00 PM", state: "busy" },
  { label: "1:30 PM", state: "busy" },
  { label: "2:00 PM", state: "available" },
  { label: "2:30 PM", state: "busy" },
  { label: "3:00 PM", state: "busy" },
  { label: "3:30 PM", state: "available" },
  { label: "4:00 PM", state: "available" },
];

export const Schedule = (): JSX.Element => {
  const [selectedDate, setSelectedDate] = useState("1");
  const [selectedTime, setSelectedTime] = useState("10:00 AM");
  const [patientType, setPatientType] = useState("Another Person");
  const [gender, setGender] = useState("Female");
  const [fullName, setFullName] = useState("Zinnatun Tasnim");
  const [age, setAge] = useState("24");
  const [problem, setProblem] = useState("");

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
  };

  return (
    <main className="bg-white w-full min-w-[360px] min-h-[800px] relative overflow-hidden">
      <div className="absolute top-0 left-0 w-[360px] h-7 bg-[#ecf1ff]" />
      <time
        className="absolute top-[9px] left-[27px] w-[30px] h-3.5 flex items-center [font-family:'League_Spartan-Medium',Helvetica] font-medium text-black text-[13px] tracking-[0] leading-[normal] whitespace-nowrap"
        dateTime="16:04"
      >
        16:04
      </time>
      <img
        className="absolute top-[9px] left-[273px] w-[13px] h-[11px]"
        alt=""
        src={vector}
      />
      <img
        className="absolute top-2.5 left-[290px] w-[17px] h-2.5"
        alt=""
        src={image}
      />
      <div
        className="absolute top-[calc(50.00%_-_389px)] left-[calc(50.00%_+_132px)] w-[17px] h-[9px]"
        aria-hidden="true"
      >
        <img
          className="absolute top-[calc(50.00%_-_4px)] left-[calc(50.00%_-_8px)] w-3 h-[7px]"
          alt=""
          src={vectorStroke}
        />
        <img
          className="absolute top-[calc(50.00%_-_5px)] left-[calc(50.00%_-_9px)] w-[18px] h-2.5"
          alt=""
          src={vectorStroke2}
        />
      </div>
      <header>
        <button
          type="button"
          className="absolute top-[54px] left-[20px] w-9 h-9 flex items-center justify-center"
          aria-label="Go back"
        >
          <img className="w-2.5 h-4" alt="" src={vector2} />
        </button>
        <nav
          className="absolute top-[59px] left-[213px] flex gap-0"
          aria-label="Quick actions"
        >
          <button
            type="button"
            className="w-[21px] h-[21px] flex bg-[#225fff] rounded-[13px]"
            aria-label="Call"
          >
            <img
              className="mt-[4.5px] w-[11px] h-3 ml-[4.5px]"
              alt=""
              src={vector8}
            />
          </button>
          <button
            type="button"
            className="w-[21px] h-[21px] flex items-center justify-center bg-[#225fff] rounded-[13px] ml-0.5"
            aria-label="Video call"
          >
            <img
              className="mt-px h-[9px] ml-px w-[13px]"
              alt=""
              src={vector7}
            />
          </button>
          <button
            type="button"
            className="w-[21px] h-[21px] flex bg-[#225fff] rounded-[13px] ml-0.5"
            aria-label="Chat"
          >
            <img
              className="mt-[4.5px] w-[13px] h-3 ml-[3.5px]"
              alt=""
              src={vector9}
            />
          </button>
          <button
            type="button"
            className="w-[21px] h-[21px] bg-[#c9d5ff] rounded-[13px] ml-0.5"
            aria-label="Help"
          >
            <img
              className="mt-[5px] ml-[7px] w-1.5 h-2.5"
              alt=""
              src={vector3}
            />
          </button>
          <button
            type="button"
            className="w-[21px] h-[21px] bg-[#c9d5ff] rounded-[13px] ml-0.5"
            aria-label="Favorite"
          >
            <img
              className="mt-[5px] ml-[5px] w-3 h-[11px]"
              alt=""
              src={vector158Stroke}
            />
          </button>
        </nav>
      </header>
      <section
        className="absolute top-[90px] left-0 w-[360px] h-[114px] bg-[#c9d5ff]"
        aria-labelledby="month-heading"
      >
        <div className="absolute top-[103px] left-[38px] [font-family:'League_Spartan-Medium',Helvetica] font-medium text-[#225fff] text-sm tracking-[0] leading-[normal] whitespace-nowrap">
          <h1 id="month-heading" className="font-inherit">
            Month
          </h1>
        </div>
        <img
          className="absolute top-[105px] left-[93px] w-2.5 h-[7px]"
          alt=""
          src={vector12}
        />
        <div
          className="absolute top-[61px] left-[23px] w-[314px] h-2.5 flex justify-between"
          aria-hidden="true"
        >
          <img
            className="-mt-px w-[8.16px] h-[12.26px] -ml-px"
            alt=""
            src={vector10}
          />
          <img
            className="-mt-px w-[8.16px] h-[12.26px]"
            alt=""
            src={vector11}
          />
        </div>
        <div className="absolute w-[284px] h-[61px] top-[36px] left-[38px] flex">
          <div className="w-[308px] h-[60.59px] relative flex gap-[9px]">
            {dates.map((date) => {
              const isSelected = selectedDate === date.day;
              return (
                <button
                  key={date.day}
                  type="button"
                  onClick={() => setSelectedDate(date.day)}
                  aria-pressed={isSelected}
                  className={`w-10 h-[61px] rounded-[18px] flex flex-col items-center justify-start shrink-0 ${
                    isSelected ? "bg-[#225fff] border border-solid" : "bg-white"
                  }`}
                >
                  <span
                    className={`mt-4 h-5 flex items-center justify-center [font-family:'League_Spartan-Medium',Helvetica] font-medium text-2xl text-center tracking-[0] leading-[normal] ${
                      isSelected
                        ? "text-white"
                        : date.muted
                          ? "text-[#a9bbfd]"
                          : "text-black"
                    }`}
                  >
                    {date.day}
                  </span>
                  <span
                    className={`mt-px h-3 flex items-center justify-center [font-family:'League_Spartan-Light',Helvetica] font-light text-xs text-center tracking-[0] leading-[normal] ${
                      isSelected
                        ? "text-white"
                        : date.muted
                          ? "text-[#a9bbfd]"
                          : "text-black"
                    }`}
                  >
                    {date.weekday}
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      </section>
      <section
        className="absolute top-[217px] left-[30px] w-[295px] h-[101px]"
        aria-labelledby="time-heading"
      >
        <h2
          id="time-heading"
          className="absolute top-0 left-[8px] [font-family:'League_Spartan-Medium',Helvetica] font-medium text-[#225fff] text-sm tracking-[0] leading-[normal] whitespace-nowrap"
        >
          Available Time
        </h2>
        <div className="absolute top-[21px] left-0 w-[295px] grid grid-cols-5 gap-x-[5px] gap-y-1">
          {timeSlots.map((slot) => {
            const isSelected = selectedTime === slot.label;
            const isBusy = slot.state === "busy";
            return (
              <button
                key={slot.label}
                type="button"
                onClick={() => setSelectedTime(slot.label)}
                aria-pressed={isSelected}
                className={`w-[55px] h-6 rounded-[18px] border border-solid border-white flex items-center justify-center [font-family:'League_Spartan-Light',Helvetica] font-light text-xs text-center tracking-[0] leading-[normal] whitespace-nowrap ${
                  isSelected
                    ? "bg-[#225fff] text-white"
                    : isBusy
                      ? "bg-[#c9d5ff] text-black"
                      : "bg-[#ecf1ff] text-[#7f9bff]"
                }`}
              >
                {slot.label}
              </button>
            );
          })}
        </div>
      </section>
      <form onSubmit={handleSubmit} aria-labelledby="patient-details-heading">
        <img
          className="top-[337px] absolute left-[33px] w-[292px] h-px object-cover"
          alt=""
          src={line1}
        />
        <section className="absolute top-[351px] left-[30px] w-[299px] h-[209px]">
          <h2
            id="patient-details-heading"
            className="absolute top-0 left-[8px] [font-family:'League_Spartan-Medium',Helvetica] font-medium text-[#225fff] text-sm tracking-[0] leading-[normal] whitespace-nowrap"
          >
            Patient Details
          </h2>
          <fieldset className="absolute top-5 left-[8px] flex gap-0 border-0 p-0 m-0">
            <legend className="sr-only">Patient type</legend>
            {["Yourself", "Another Person"].map((option) => {
              const isSelected = patientType === option;
              return (
                <button
                  key={option}
                  type="button"
                  onClick={() => setPatientType(option)}
                  aria-pressed={isSelected}
                  className={`h-[18px] rounded-[18px] border border-solid [font-family:'League_Spartan-Light',Helvetica] font-light text-xs text-center tracking-[0] leading-[normal] whitespace-nowrap ${
                    option === "Yourself" ? "w-[62px]" : "w-[87px] ml-0.5"
                  } ${isSelected ? "bg-[#225fff] text-white border-transparent" : "text-[#7f9bff] border-[#a9bbfd]"}`}
                >
                  {option}
                </button>
              );
            })}
          </fieldset>
          <label
            htmlFor="full-name"
            className="absolute top-[58px] left-[8px] [font-family:'League_Spartan-Light',Helvetica] font-light text-black text-xs tracking-[0] leading-[normal] whitespace-nowrap"
          >
            Full Name
          </label>
          <input
            id="full-name"
            name="fullName"
            value={fullName}
            onChange={(event) => setFullName(event.target.value)}
            className="absolute top-[69px] left-0 w-[299px] h-[35px] bg-[#ecf1ff] rounded-[13px] px-[19px] [font-family:'League_Spartan-Medium',Helvetica] font-medium text-[#7f9bff] text-sm tracking-[0] leading-[normal]"
          />
          <label
            htmlFor="age"
            className="absolute top-[117px] left-[8px] [font-family:'League_Spartan-Light',Helvetica] font-light text-black text-xs tracking-[0] leading-[normal] whitespace-nowrap"
          >
            Age
          </label>
          <input
            id="age"
            name="age"
            inputMode="numeric"
            value={age}
            onChange={(event) => setAge(event.target.value)}
            className="absolute top-[131px] left-0 w-[299px] h-[35px] bg-[#ecf1ff] rounded-[13px] px-[19px] [font-family:'League_Spartan-Medium',Helvetica] font-medium text-[#7f9bff] text-sm tracking-[0] leading-[normal]"
          />
          <fieldset className="absolute top-[176px] left-0 border-0 p-0 m-0">
            <legend className="absolute -top-[13px] left-[8px] [font-family:'League_Spartan-Light',Helvetica] font-light text-black text-xs tracking-[0] leading-[normal] whitespace-nowrap">
              Gender
            </legend>
            <div className="flex gap-[7px]">
              {["Male", "Female", "Other"].map((option) => {
                const isSelected = gender === option;
                const widths: Record<string, string> = {
                  Male: "w-[62px]",
                  Female: "w-[61px]",
                  Other: "w-[62px]",
                };
                return (
                  <button
                    key={option}
                    type="button"
                    onClick={() => setGender(option)}
                    aria-pressed={isSelected}
                    className={`${widths[option]} h-[18px] rounded-[18px] border border-solid [font-family:'League_Spartan-Light',Helvetica] font-light text-sm text-center tracking-[0] leading-[normal] whitespace-nowrap ${
                      isSelected
                        ? "bg-[#225fff] text-white border-transparent"
                        : "text-[#7f9bff] border-[#cad6ff]"
                    }`}
                  >
                    {option}
                  </button>
                );
              })}
            </div>
          </fieldset>
        </section>
        <img
          className="top-[579px] absolute left-[33px] w-[292px] h-px object-cover"
          alt=""
          src={line2}
        />
        <section
          className="absolute top-[593px] left-[30px] w-[299px] h-[120px]"
          aria-labelledby="problem-label"
        >
          <label
            id="problem-label"
            htmlFor="problem"
            className="absolute top-0 left-[8px] [font-family:'League_Spartan-Light',Helvetica] font-light text-black text-xs tracking-[0] leading-[normal] whitespace-nowrap"
          >
            Describe your problem
          </label>
          <textarea
            id="problem"
            name="problem"
            value={problem}
            onChange={(event) => setProblem(event.target.value)}
            placeholder="Enter Your Problem ."
            className="absolute top-[13px] left-0 w-[295px] h-[107px] resize-none rounded-[18px] border border-solid border-[#cad6ff] px-[23px] pt-[10px] [font-family:'League_Spartan-Light',Helvetica] font-light text-[#070707] placeholder:text-[#070707] text-xs tracking-[0] leading-[normal]"
          />
        </section>
        <nav
          className="absolute top-[733px] left-[31px] w-[298px] h-12 bg-[#225fff] rounded-3xl"
          aria-label="Main navigation"
        >
          <div className="absolute top-[15px] left-[63px] w-[172px] h-[23px] flex gap-[52px]">
            <button
              type="button"
              className="w-[24.01px] h-6 -mt-[0.5px] -ml-[0.5px]"
              aria-label="Home"
            >
              <img className="w-[24.01px] h-6" alt="" src={vector4} />
            </button>
            <button
              type="button"
              className="w-[25px] h-[22px] -mt-[0.5px]"
              aria-label="Messages"
            >
              <img className="w-[25px] h-[22px]" alt="" src={vector5} />
            </button>
            <button
              type="submit"
              className="w-5 h-[22px] -mt-[0.5px]"
              aria-label="Confirm appointment"
            >
              <img className="w-5 h-[22px]" alt="" src={vector6} />
            </button>
          </div>
        </nav>
      </form>
    </main>
  );
};
