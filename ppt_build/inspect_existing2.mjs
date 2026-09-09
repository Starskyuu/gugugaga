import { installNode } from '@oai/granola/node';
import { Presentation } from '@oai/artifact-tool';
installNode();
const deck = await Presentation.load('F:/gugugaga/GPS_YOLO_定位方案.pptx');
const result = await deck.inspect({kind:'slide,textbox,shape,layout',maxChars:12000});
console.log(result.ndjson);
