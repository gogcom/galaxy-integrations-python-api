stage('Upload to github')
{
    node('ActiveClientMacosxBuilder') {
        deleteDir()
        checkout scm
        withPythonEnv('python') {
            withCredentials([usernamePassword(credentialsId: 'github_friendsofgalaxy', usernameVariable: 'GITHUB_USERNAME', passwordVariable: 'GITHUB_TOKEN')]) {
                sh 'pip install -r jenkins/requirements.txt'
                def version = sh(returnStdout: true, script: 'python setup.py --version').trim()
                sh "python jenkins/release.py $version"
            }
        }
    }
}
