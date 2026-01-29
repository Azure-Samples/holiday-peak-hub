import { faker } from "@faker-js/faker";
import { format } from "date-fns";
import {Task, randomElement} from "@/components/tasks";

export const generateTasks = (n: number): Task[] => {
  return Array.from(Array(n).keys()).map((i) => {
    const img: number = randomElement<number>(Array.from(Array(9).keys())) + 1;
    return {
      id: i,
      title: faker.lorem.sentence(),
      done: false,
      category: randomElement(["To do", "In Progress", "Code Review"]),
      date: format(new Date(), "MMM dd"),
      img: `/images/faces/${randomElement(["m", "w"])}${img}.png`,
      badge: {
        title: randomElement(["low", "high", "medium", "important", "new"]),
        color: randomElement([
          "bg-green-700 text-green-100",
          "bg-yellow-700 text-yellow-100",
          "bg-red-700 text-red-100",
          "bg-blue-700 text-blue-100",
          "bg-pink-700 text-pink-100",
        ]),
      },
    };
  });
};
