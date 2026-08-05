import python
import semmle.python.security.dataflow.SqlInjection
import semmle.python.ApiGraphs

from DataFlow::Node source, DataFlow::Node sink, string fileName
where
exists(SqlInjection::Configuration config |
config.hasFlow(source, sink)
) and
fileName = sink.getLocation().getFile().getRelativePath()

select sink,
"Potential SQL injection vulnerability detected with user input from $@ in file '" + fileName + "'.",
source, source.toString()
