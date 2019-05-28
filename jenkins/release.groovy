stage('Upload to github')
{
    node('ActiveClientMacosxBuilder') {
        deleteDir()
        checkout scm
        withPythonEnv('/usr/local/bin/python3.7') {
            withCredentials([string(credentialsId: 'github_goggalaxy', variable: 'GITHUB_TOKEN')]) {
                sh 'pip install -r jenkins/requirements.txt'
                def version = sh(returnStdout: true, script: 'python setup.py --version').trim()
                sh "python jenkins/release.py $version"
            }
        }
    }
}
