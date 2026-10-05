import javax.xml.parsers.*; import org.xml.sax.*; import org.xml.sax.helpers.*; import java.io.*; import java.nio.file.*; import java.util.*;
public class XmlBatch {
  public static void main(String[] a) throws Exception {
    SAXParserFactory f = SAXParserFactory.newInstance(); f.setNamespaceAware(true);
    List<String> lines = Files.readAllLines(Paths.get(a[0]));
    StringBuilder sb = new StringBuilder();
    for (int i=0;i<lines.size();i++){
      int rc=0;
      try {
        XMLReader r=f.newSAXParser().getXMLReader();
        r.setErrorHandler(new DefaultHandler(){ public void error(SAXParseException e)throws SAXException{throw e;} public void fatalError(SAXParseException e)throws SAXException{throw e;} });
        try (FileInputStream input = new FileInputStream(lines.get(i))) {
          r.parse(new InputSource(input));
        }
      } catch (SAXException e){ rc=1; }
      sb.append(i).append(' ').append(rc).append('\n');
    }
    System.out.print(sb);
  }
}
