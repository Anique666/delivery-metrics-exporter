// 02-job.groovy
// Creates (or updates) the "Pipeline script from SCM" job that points at the
// GitHub repository, branch main and the Jenkinsfile at the repository root.
import hudson.model.BooleanParameterDefinition
import hudson.model.ParametersDefinitionProperty
import hudson.plugins.git.BranchSpec
import hudson.plugins.git.GitSCM
import hudson.plugins.git.UserRemoteConfig
import jenkins.model.Jenkins
import org.jenkinsci.plugins.workflow.cps.CpsScmFlowDefinition
import org.jenkinsci.plugins.workflow.job.WorkflowJob

def instance = Jenkins.getInstanceOrNull()
if (instance == null) {
    return
}

def env = System.getenv()
def repoUrl = env.get('GITHUB_REPO_URL') ?: 'https://github.com/Anique666/delivery-metrics-exporter.git'
def branch = env.get('GITHUB_BRANCH') ?: '*/main'
def jobName = env.get('JENKINS_JOB_NAME') ?: 'delivery-metrics-exporter'

def job = instance.getItem(jobName) as WorkflowJob
if (job == null) {
    job = instance.createProject(WorkflowJob, jobName)
    println "[init] created job '${jobName}'"
}

def scm = new GitSCM(
    [new UserRemoteConfig(repoUrl, null, null, null)],
    [new BranchSpec(branch)],
    false, [], null, null, []
)
def definition = new CpsScmFlowDefinition(scm, 'Jenkinsfile')
definition.setLightweight(true)
job.setDefinition(definition)

job.setDescription(
    'Delivery Metrics Exporter - declarative pipeline defined in the Jenkinsfile ' +
    "stored in ${repoUrl} (branch ${branch}). Pipeline script from SCM."
)

def parameters = new ParametersDefinitionProperty(
    new BooleanParameterDefinition(
        'DEMO_FORCE_TEST_FAILURE',
        false,
        'Examination demo only: when checked, the automated test stage fails on purpose so Jenkins reports a FAILURE build.'
    )
)
job.addProperty(parameters)
job.save()

println "[init] job '${jobName}' -> ${repoUrl} [${branch}] scriptPath=Jenkinsfile"
